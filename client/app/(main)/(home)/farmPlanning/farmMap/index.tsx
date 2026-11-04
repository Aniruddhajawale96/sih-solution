import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from "react-native";
import MapView, {
  Marker,
  Polygon,
  Polyline,
  PROVIDER_GOOGLE,
  Region,
} from "react-native-maps";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "@/hooks/useTheme";
import SIZES from "@/constants/sizes";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";
import { router } from "expo-router";
import { INDIA_REGION } from "@/store/map/map";
import * as Location from "expo-location";
import type { Point } from "@/types/map/map";
import useAppStore from "@/store";
import { generateFarmSVG, splitFarmByLines } from "@/lib/methods/cutPolygon";
import { setFarmBoundary } from "@/lib/api/farm";
import { getRecommendation, type SoilSection } from "@/lib/api/model";

type SplitLine = {
  id: string;
  points: { latitude: number; longitude: number }[];
};

type WorkflowStep = "marking" | "confirmed" | "sectioning" | "finished";

const FarmBoundaryMap = () => {
  const styles = useStyles();
  const colors = useTheme();
  const mapRef = React.useRef<MapView>(null);
  const { setSvg, soilType, budget, setRecommendations } = useAppStore();

  const [step, setStep] = useState<WorkflowStep>("marking");
  const [points, setPoints] = useState<Point[]>([]);
  const [sectionLines, setSectionLines] = useState<SplitLine[]>([]);
  const [currentLineStart, setCurrentLineStart] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [currentLineEnd, setCurrentLineEnd] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [tempLineEnd, setTempLineEnd] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [savedBoundary, setSavedBoundary] = useState<any>(null);
  const [isLoadingRecommendation, setIsLoadingRecommendation] = useState(false);

  // History for undo/redo
  const [boundaryHistory, setBoundaryHistory] = useState<Point[][]>([[]]);
  const [boundaryHistoryIndex, setBoundaryHistoryIndex] = useState(0);
  const [sectionHistory, setSectionHistory] = useState<SplitLine[][]>([[]]);
  const [sectionHistoryIndex, setSectionHistoryIndex] = useState(0);

  const zoomToLocation = (coords: Location.LocationObjectCoords) => {
    const { latitude, longitude } = coords;

    const farmerRegion: Region = {
      latitude,
      longitude,
      latitudeDelta: 0.002,
      longitudeDelta: 0.002,
    };

    mapRef.current?.animateToRegion(farmerRegion, 800);
  };

  useEffect(() => {
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        console.error("Permission to access location was denied");
        return;
      }

      const lastLocation = await Location.getLastKnownPositionAsync();

      if (lastLocation) {
        if (__DEV__) {
          lastLocation.coords.latitude = 19.150142908770977;
          lastLocation.coords.longitude = 74.11448497989491;
        }
        zoomToLocation(lastLocation.coords);
      } else {
        const currentLocation = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        if (__DEV__) {
          currentLocation.coords.latitude = 19.150142908770977;
          currentLocation.coords.longitude = 74.11448497989491;
        }
        zoomToLocation(currentLocation.coords);
      }
    })();
  }, []);

  const addToBoundaryHistory = (newPoints: Point[]) => {
    const newHistory = boundaryHistory.slice(0, boundaryHistoryIndex + 1);
    newHistory.push(newPoints);
    setBoundaryHistory(newHistory);
    setBoundaryHistoryIndex(newHistory.length - 1);
    setPoints(newPoints);
  };

  const addToSectionHistory = (newLines: SplitLine[]) => {
    const newHistory = sectionHistory.slice(0, sectionHistoryIndex + 1);
    newHistory.push(newLines);
    setSectionHistory(newHistory);
    setSectionHistoryIndex(newHistory.length - 1);
    setSectionLines(newLines);
  };

  const handleMapPress = (event: any) => {
    const { coordinate } = event.nativeEvent;

    if (step === "marking") {
      // Add boundary points
      const newPoint: Point = {
        latitude: coordinate.latitude,
        longitude: coordinate.longitude,
        id: points.length + 1,
      };
      addToBoundaryHistory([...points, newPoint]);
    } else if (step === "sectioning") {
      // Draw straight line - toggle between start and end
      if (!currentLineStart) {
        // Set start point
        setCurrentLineStart(coordinate);
        setTempLineEnd(null);
      } else if (!currentLineEnd) {
        // Set end point and save the line
        setCurrentLineEnd(coordinate);

        // Create straight line with just two points
        const newLine: SplitLine = {
          id: `line-${Date.now()}`,
          points: [currentLineStart, coordinate],
        };

        addToSectionHistory([...sectionLines, newLine]);

        // Reset for next line
        setCurrentLineStart(null);
        setCurrentLineEnd(null);
        setTempLineEnd(null);
      }
    }
  };

  const handleUndo = () => {
    if (step === "marking") {
      if (boundaryHistoryIndex > 0) {
        const newIndex = boundaryHistoryIndex - 1;
        setBoundaryHistoryIndex(newIndex);
        setPoints(boundaryHistory[newIndex]);
      }
    } else if (step === "sectioning") {
      // If currently drawing a line, cancel it
      if (currentLineStart) {
        setCurrentLineStart(null);
        setCurrentLineEnd(null);
        setTempLineEnd(null);
      } else if (sectionHistoryIndex > 0) {
        // Otherwise undo last saved line
        const newIndex = sectionHistoryIndex - 1;
        setSectionHistoryIndex(newIndex);
        setSectionLines(sectionHistory[newIndex]);
      }
    }
  };

  const handleRedo = () => {
    if (step === "marking") {
      if (boundaryHistoryIndex < boundaryHistory.length - 1) {
        const newIndex = boundaryHistoryIndex + 1;
        setBoundaryHistoryIndex(newIndex);
        setPoints(boundaryHistory[newIndex]);
      }
    } else if (step === "sectioning") {
      if (sectionHistoryIndex < sectionHistory.length - 1) {
        const newIndex = sectionHistoryIndex + 1;
        setSectionHistoryIndex(newIndex);
        setSectionLines(sectionHistory[newIndex]);
      }
    }
  };

  const handleClear = () => {
    if (step === "marking") {
      Alert.alert(
        "Clear All Points",
        "Are you sure you want to clear all marked points?",
        [
          { text: "Cancel", style: "cancel" },
          {
            text: "Clear",
            style: "destructive",
            onPress: () => {
              addToBoundaryHistory([]);
            },
          },
        ],
      );
    } else if (step === "sectioning") {
      // If currently drawing, clear the current line
      if (currentLineStart) {
        setCurrentLineStart(null);
        setCurrentLineEnd(null);
        setTempLineEnd(null);
      } else {
        // Otherwise clear all section lines
        Alert.alert(
          "Clear All Sections",
          "Are you sure you want to clear all section lines?",
          [
            { text: "Cancel", style: "cancel" },
            {
              text: "Clear",
              style: "destructive",
              onPress: () => {
                addToSectionHistory([]);
              },
            },
          ],
        );
      }
    }
  };

  const handleConfirm = async () => {
    if (points.length < 3) {
      Alert.alert(
        "Insufficient Points",
        "Please mark at least 3 points to create a boundary.",
      );
      return;
    }

    try {
      const formattedBoundary = points.map(({ latitude, longitude }) => ({
        latitude,
        longitude,
      }));
      const data = await setFarmBoundary({ formattedBoundary });

      console.log("Boundary saved successfully:", data);
      setSavedBoundary(data);
      setStep("confirmed");
    } catch (error) {
      console.error("Error saving boundary:", error);
      Alert.alert("Error", "Failed to save boundary. Please try again.");
    }
  };

  const handleAddSections = () => {
    setStep("sectioning");
    // Initialize section history
    setSectionHistory([[]]);
    setSectionHistoryIndex(0);
  };

  const handleFinish = async () => {
    if (!savedBoundary) {
      Alert.alert("Error", "Boundary data not found.");
      return;
    }

    try {
      let zones: { x: number; y: number }[][];

      if (sectionLines.length === 0) {
        // No sections - just use the outer boundary
        zones = [savedBoundary.polygon_2d];
        console.log("No section lines - using boundary only");
      } else {
        // Split by straight lines using intersection logic
        const formattedBoundary = points.map(({ latitude, longitude }) => ({
          latitude,
          longitude,
        }));

        const formattedLines = sectionLines.map((line) => line.points);

        console.log(`Splitting with ${formattedLines.length} lines...`);
        zones = splitFarmByLines(formattedBoundary, formattedLines);
        console.log(`Created ${zones.length} zones`);

        // Debug: log zone info
        zones.forEach((zone, idx) => {
          console.log(`Zone ${idx + 1}: ${zone.length} points`);
        });
      }

      // Generate colors based on actual zone count
      const colors =
        zones.length === 1
          ? ["#a3d1a3"]
          : zones.map((_, idx) => {
              const hue = (idx * 137.5) % 360; // Golden angle for color distribution
              return `hsl(${hue}, 45%, 60%)`;
            });

      const svg = generateFarmSVG(savedBoundary.polygon_2d, zones, {
        colors,
        stroke: "#2f4f2f",
        strokeWidth: 1.5,
      });

      setSvg(svg);
      console.log("Generated SVG with", zones.length, "zones");
      console.log(svg);
      setStep("finished");

      // Get farm center for location
      const latitudes = points.map((p) => p.latitude);
      const longitudes = points.map((p) => p.longitude);
      const centerLat = latitudes.reduce((a, b) => a + b, 0) / latitudes.length;
      const centerLng =
        longitudes.reduce((a, b) => a + b, 0) / longitudes.length;

      // Prepare soil sections data
      const soilSections: SoilSection[] = zones.map((zone, idx) => ({
        section_name: String.fromCharCode(65 + idx), // A, B, C, etc.
        water_source: "Canal", // Default, can be customized
        near_water: true, // Default, can be customized
      }));

      // Prepare recommendation request
      const recommendationData = {
        location: {
          latitude: centerLat,
          longitude: centerLng,
        },
        soil_type: soilType,
        soil_sections: soilSections,
        budget: budget || 100000,
        crop_type: "kharif", // Default, can be customized based on season
      };

      console.log("Requesting recommendations with data:", recommendationData);

      // Show loading state
      setIsLoadingRecommendation(true);

      try {
        // Call recommendation API
        const recommendations = await getRecommendation(recommendationData);
        console.log("Received recommendations:", recommendations);
        for (const a in recommendations?.recommendations) {
          console.log(a);
        }

        setRecommendations(recommendations.recommendations);

        Alert.alert(
          "Success",
          `Farm boundary with ${zones.length} section${zones.length !== 1 ? "s" : ""} created successfully!\n\nRecommendations received for all sections.`,
          [
            {
              text: "View 3D Model",
              onPress: () => {
                router.replace("/(main)/(home)/farmPlanning/farmMap3D");
              },
            },
          ],
        );
      } catch (error) {
        console.error("Error getting recommendations:", error);
        Alert.alert(
          "Partial Success",
          `Farm boundary created, but failed to get crop recommendations. You can still view the 3D model.`,
          [
            {
              text: "View 3D Model",
              onPress: () => {
                router.replace("/(main)/(home)/farmPlanning/farmMap3D");
              },
            },
          ],
        );
      } finally {
        setIsLoadingRecommendation(false);
      }
    } catch (error) {
      console.error("Error generating SVG:", error);
      Alert.alert(
        "Error",
        "Failed to generate farm visualization. " + (error as Error).message,
      );
    }
  };

  const canUndo = () => {
    if (step === "marking") {
      return boundaryHistoryIndex > 0;
    } else if (step === "sectioning") {
      return currentLineStart !== null || sectionHistoryIndex > 0;
    }
    return false;
  };

  const canRedo = () => {
    if (step === "marking") {
      return boundaryHistoryIndex < boundaryHistory.length - 1;
    } else if (step === "sectioning") {
      return sectionHistoryIndex < sectionHistory.length - 1;
    }
    return false;
  };

  const canClear = () => {
    if (step === "marking") {
      return points.length > 0;
    } else if (step === "sectioning") {
      return currentLineStart !== null || sectionLines.length > 0;
    }
    return false;
  };

  const renderButtons = () => {
    if (step === "marking") {
      return (
        <>
          <TouchableOpacity
            style={[
              styles.button,
              styles.clearButton,
              !canClear() && styles.disabledButton,
            ]}
            onPress={handleClear}
            disabled={!canClear()}
          >
            <Text style={styles.buttonText}>Clear</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.button,
              styles.undoButton,
              !canUndo() && styles.disabledButton,
            ]}
            onPress={handleUndo}
            disabled={!canUndo()}
          >
            <Text style={styles.buttonText}>Undo</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.button,
              styles.confirmButton,
              points.length < 3 && styles.disabledButton,
            ]}
            onPress={handleConfirm}
            disabled={points.length < 3}
          >
            <Text style={[styles.buttonText, styles.confirmButtonText]}>
              Confirm
            </Text>
          </TouchableOpacity>
        </>
      );
    }

    if (step === "confirmed") {
      return (
        <>
          <TouchableOpacity
            style={[styles.button, styles.confirmButton]}
            onPress={handleAddSections}
          >
            <Text style={[styles.buttonText, styles.confirmButtonText]}>
              Add Sections
            </Text>
          </TouchableOpacity>
        </>
      );
    }

    if (step === "sectioning") {
      return (
        <>
          <TouchableOpacity
            style={[
              styles.button,
              styles.clearButton,
              !canClear() && styles.disabledButton,
            ]}
            onPress={handleClear}
            disabled={!canClear()}
          >
            <Text style={styles.buttonText}>
              {currentLineStart ? "Cancel Line" : "Clear All"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.button,
              styles.undoButton,
              !canUndo() && styles.disabledButton,
            ]}
            onPress={handleUndo}
            disabled={!canUndo()}
          >
            <Text style={styles.buttonText}>Undo</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.button,
              styles.finishButton,
              isLoadingRecommendation && styles.disabledButton,
            ]}
            onPress={handleFinish}
            disabled={isLoadingRecommendation}
          >
            {isLoadingRecommendation ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={[styles.buttonText, styles.finishButtonText]}>
                Finish
              </Text>
            )}
          </TouchableOpacity>
        </>
      );
    }

    return null;
  };

  const renderSectionInfo = () => {
    if (step === "sectioning") {
      return (
        <View style={styles.infoContainer}>
          <Text style={styles.infoText}>
            {currentLineStart
              ? "Tap to set end point"
              : `Sections: ${sectionLines.length} | Tap to draw line`}
          </Text>
          {canRedo() && (
            <TouchableOpacity onPress={handleRedo}>
              <Text style={styles.redoText}>Redo</Text>
            </TouchableOpacity>
          )}
        </View>
      );
    } else if (step === "marking" && canRedo()) {
      return (
        <View style={styles.infoContainer}>
          <Text style={styles.infoText}>Points: {points.length}</Text>
          <TouchableOpacity onPress={handleRedo}>
            <Text style={styles.redoText}>Redo</Text>
          </TouchableOpacity>
        </View>
      );
    }
    return null;
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <MapView
        ref={mapRef}
        provider={PROVIDER_GOOGLE}
        showsUserLocation
        zoomEnabled
        style={styles.map}
        initialRegion={INDIA_REGION}
        onPress={handleMapPress}
        onLongPress={(event) => {
          // Update temp line end while dragging
          if (step === "sectioning" && currentLineStart && !currentLineEnd) {
            setTempLineEnd(event.nativeEvent.coordinate);
          }
        }}
        onPanDrag={(event) => {
          // Update temp line end while panning
          if (step === "sectioning" && currentLineStart && !currentLineEnd) {
            setTempLineEnd(event.nativeEvent.coordinate);
          }
        }}
        mapType={"satellite"}
        compassOffset={{ x: 20, y: 100 }}
      >
        {/* Draw boundary polygon */}
        {points.length >= 3 && (
          <Polygon
            coordinates={points}
            strokeColor={colors.primary}
            fillColor="rgba(0, 122, 255, 0.2)"
            strokeWidth={2}
          />
        )}

        {/* Draw lines between consecutive boundary points */}
        {points.length >= 2 &&
          points.map((point, index) => {
            if (index === points.length - 1) return null;
            return (
              <Polyline
                key={`boundary-line-${index}`}
                coordinates={[point, points[index + 1]]}
                strokeColor={colors.primary}
                strokeWidth={2}
              />
            );
          })}

        {/* Draw boundary markers */}
        {points.map((point) => (
          <Marker key={point.id} coordinate={point} anchor={{ x: 0.5, y: 0.5 }}>
            <View style={styles.markerContainer}>
              <View style={styles.marker}>
                <Text style={styles.markerText}>{point.id}</Text>
              </View>
            </View>
          </Marker>
        ))}

        {/* Draw saved section lines (straight lines) */}
        {sectionLines.map((line, idx) => (
          <React.Fragment key={line.id}>
            <Polyline
              coordinates={line.points}
              strokeColor="#FF9500"
              strokeWidth={4}
            />
            {/* Draw markers at exact line endpoints */}
            <Marker
              coordinate={line.points[0]}
              anchor={{ x: 0.5, y: 0.5 }}
              centerOffset={{ x: 0, y: 0 }}
              flat
            >
              <View style={styles.sectionMarkerContainer}>
                <View style={styles.sectionMarker}>
                  <Text style={styles.sectionMarkerText}>{idx * 2 + 1}</Text>
                </View>
              </View>
            </Marker>
            <Marker
              coordinate={line.points[1]}
              anchor={{ x: 0.5, y: 0.5 }}
              centerOffset={{ x: 0, y: 0 }}
              flat
            >
              <View style={styles.sectionMarkerContainer}>
                <View style={styles.sectionMarker}>
                  <Text style={styles.sectionMarkerText}>{idx * 2 + 2}</Text>
                </View>
              </View>
            </Marker>
          </React.Fragment>
        ))}

        {/* Draw current section line being created */}
        {currentLineStart && (
          <>
            <Marker
              coordinate={currentLineStart}
              anchor={{ x: 0.5, y: 0.5 }}
              centerOffset={{ x: 0, y: 0 }}
              flat
            >
              <View style={styles.sectionMarkerContainer}>
                <View style={[styles.sectionMarker, styles.activeMarker]}>
                  <Text style={styles.sectionMarkerText}>●</Text>
                </View>
              </View>
            </Marker>
            {/* Show preview line if we have a temporary end point */}
            {tempLineEnd && (
              <Polyline
                coordinates={[currentLineStart, tempLineEnd]}
                strokeColor="#FFD700"
                strokeWidth={3}
                lineDashPattern={[8, 4]}
              />
            )}
          </>
        )}
      </MapView>

      {renderSectionInfo()}

      <View style={styles.buttonContainer}>{renderButtons()}</View>
    </SafeAreaView>
  );
};

const useStyles = () => {
  const colors = useTheme();
  return StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    map: {
      flex: 1,
    },
    markerContainer: {
      alignItems: "center",
      justifyContent: "center",
    },
    marker: {
      backgroundColor: colors.primary,
      width: SIZES.icon.XL,
      height: SIZES.icon.XL,
      borderRadius: SIZES.radius.FULL,
      alignItems: "center",
      justifyContent: "center",
      borderWidth: SIZES.spacing.SPACING_4,
      borderColor: colors.border,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.3,
      shadowRadius: 3,
      elevation: 5,
    },
    markerText: {
      borderColor: colors.border,
      fontSize: FONT_SIZES.sm,
      fontWeight: FONT_WEIGHTS.bold,
    },
    sectionMarkerContainer: {
      width: SIZES.icon.LG,
      height: SIZES.icon.LG,
      alignItems: "center",
      justifyContent: "center",
    },
    sectionMarker: {
      backgroundColor: "#FF9500",
      width: SIZES.icon.LG,
      height: SIZES.icon.LG,
      borderRadius: SIZES.radius.FULL,
      borderWidth: 1,
      borderColor: "#fff",
      alignItems: "center",
      justifyContent: "center",
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.3,
      shadowRadius: 3,
      elevation: 5,
    },
    activeMarker: {
      backgroundColor: "#FFD700",
    },
    sectionMarkerText: {
      color: colors.text,
      fontSize: FONT_SIZES.xs,
      fontWeight: FONT_WEIGHTS.bold,
    },
    infoContainer: {
      position: "absolute",
      top: 60,
      left: 20,
      right: 20,
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      padding: SIZES.spacing.SPACING_12,
      borderRadius: SIZES.radius.MD,
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
    },
    infoText: {
      fontSize: FONT_SIZES.sm,
      fontWeight: FONT_WEIGHTS.medium,
      color: "#333",
    },
    redoText: {
      fontSize: FONT_SIZES.sm,
      fontWeight: FONT_WEIGHTS.semibold,
      color: colors.primary,
    },
    buttonContainer: {
      flexDirection: "row",
      position: "absolute",
      bottom: 20,
      left: 20,
      right: 20,
      justifyContent: "space-between",
      padding: SIZES.spacing.SPACING_20,
      gap: SIZES.spacing.SPACING_12,
    },
    button: {
      flex: 1,
      paddingVertical: SIZES.spacing.SPACING_16,
      borderRadius: SIZES.radius.MD,
      alignItems: "center",
      justifyContent: "center",
    },
    clearButton: {
      backgroundColor: colors.error,
    },
    undoButton: {
      backgroundColor: colors.warning,
    },
    confirmButton: {
      backgroundColor: colors.primary,
    },
    finishButton: {
      backgroundColor: colors.success,
    },
    disabledButton: {
      backgroundColor: "#999",
      opacity: 0.5,
    },
    buttonText: {
      color: colors.text,
      fontSize: FONT_SIZES.md,
      fontWeight: FONT_WEIGHTS.semibold,
    },
    confirmButtonText: {
      fontSize: FONT_SIZES.md,
    },
    finishButtonText: {
      fontSize: FONT_SIZES.md,
    },
  });
};

export default FarmBoundaryMap;
