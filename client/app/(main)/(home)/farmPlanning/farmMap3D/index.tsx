import {
  ScrollView,
  StyleSheet,
  Platform,
  Dimensions,
  View,
  Text,
} from "react-native";
import React, { useMemo, useState, useRef } from "react";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";
import { useTheme } from "@/hooks/useTheme";
import { useTranslation } from "react-i18next";

import { Canvas, useFrame, useThree } from "@react-three/fiber/native";
import { SVGLoader } from "three/examples/jsm/loaders/SVGLoader.js";
import * as THREE from "three";
import { extractViewBox } from "@/lib/methods/extractViewBox";
import useAppStore from "@/store";
import CropBase from "./components/CropBase";
import { Asset } from "expo-asset";
import { ZoomButtons } from "@/lib/helpers/controllers/ZoomButtons";
import { OrbitControls } from "@react-three/drei/native";
import CropInfoCard from "./components/CropInfoCard";
import { CropKey } from "@/types/crops";
import { CROP_INFO } from "@/constants/defaults";

const SECTION_COLORS = [
  "#3E2723", // very dark moist soil
  "#5D4037", // dark brown
  "#7A4A2E", // medium soil
  "#9C6B43", // dry brown
  "#C9A26D", // sandy / light soil
] as const;

// Fallback crop selection based on available models
const FALLBACK_CROPS: CropKey[] = ["wheat", "corn", "onion"];

function getRandomSectionColor() {
  return SECTION_COLORS[Math.floor(Math.random() * SECTION_COLORS.length)];
}

// Easing function for smooth animation
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// Camera animation component
function CameraAnimation({
  targetPosition,
  startAnimation,
  duration = 1200,
}: {
  targetPosition: [number, number, number];
  startAnimation: boolean;
  duration?: number;
}) {
  const startTime = useRef<number | null>(null);
  const startPosition = useRef<THREE.Vector3 | null>(null);
  const hasAnimated = useRef(false);
  const { camera } = useThree();

  useFrame(() => {
    if (hasAnimated.current || !startAnimation) return;

    if (!startPosition.current) {
      // Start from a position further back and to the side for curved motion
      const radius = Math.sqrt(
        targetPosition[1] * targetPosition[1] +
          targetPosition[2] * targetPosition[2],
      );

      startPosition.current = new THREE.Vector3(
        targetPosition[0] + radius * 0.8, // Offset to the side
        targetPosition[1] * 2, // Higher up
        targetPosition[2] * 2, // Further back
      );
      camera.position.copy(startPosition.current);
      camera.lookAt(0, 0, 0); // Look at center
      startTime.current = Date.now();
    }

    if (!startTime.current) return;

    const elapsed = Date.now() - startTime.current;
    const progress = Math.min(elapsed / duration, 1);

    if (progress < 1) {
      const easedProgress = easeInOutCubic(progress);

      // Create a curved path using a quadratic bezier curve
      const start = startPosition.current;
      const end = new THREE.Vector3(...targetPosition);

      // Control point for the curve (creates an arc)
      const controlPoint = new THREE.Vector3(
        (start.x + end.x) / 2 - targetPosition[2] * 0.5, // Curve to the left
        (start.y + end.y) / 2 + targetPosition[1] * 0.3, // Slight arc upward
        (start.z + end.z) / 2,
      );

      // Quadratic bezier interpolation
      const t = easedProgress;
      const invT = 1 - t;

      camera.position.set(
        invT * invT * start.x + 2 * invT * t * controlPoint.x + t * t * end.x,
        invT * invT * start.y + 2 * invT * t * controlPoint.y + t * t * end.y,
        invT * invT * start.z + 2 * invT * t * controlPoint.z + t * t * end.z,
      );

      // Always look at the center of the scene
      camera.lookAt(0, 0, 0);
    } else {
      camera.position.set(...targetPosition);
      camera.lookAt(0, 0, 0);
      hasAnimated.current = true;
    }
  });

  return null;
}

// Scene readiness detector
function SceneReadyDetector({ onReady }: { onReady: () => void }) {
  const readyCalled = useRef(false);

  useFrame(() => {
    if (!readyCalled.current) {
      // Wait one frame to ensure everything is rendered
      setTimeout(() => {
        if (!readyCalled.current) {
          readyCalled.current = true;
          onReady();
        }
      }, 100);
    }
  });

  return null;
}

const FarmPlanning = () => {
  const styles = useStyles();
  const insets = useSafeAreaInsets();
  const { t } = useTranslation();
  const svg = useAppStore((state) => state.svg);
  const { recommendations } = useAppStore();
  const cameraRef = useRef<THREE.PerspectiveCamera>(null);

  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [sceneReady, setSceneReady] = useState(false);

  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(
    null,
  );

  console.log(recommendations, "helloooo");
  const [selectedCrop, setSelectedCrop] = useState<CropKey | null>(null);

  const handleSelect = (sectionId: string, crop: CropKey) => {
    setSelectedSectionId((prev) => (prev === sectionId ? null : sectionId));
    setSelectedCrop(crop);
  };

  React.useEffect(() => {
    async function loadAssets() {
      await Asset.loadAsync([
        require("@/assets/models/wheat.glb"),
        require("@/assets/models/rice.glb"),
        require("@/assets/models/corn.glb"),
        require("@/assets/models/maize.glb"),
        require("@/assets/models/sugarcane.glb"),
        require("@/assets/models/abc.glb"),
      ]);
      setAssetsLoaded(true);
    }

    loadAssets();
  }, []);

  // Map crop names from recommendations to available CropKey types
  const getCropMapping = (cropName: string): CropKey => {
    const cropMap: Record<string, CropKey> = {
      bajra: "wheat", // Map bajra to wheat model
      groundnut: "rice", // Map groundnut to rice model
      wheat: "wheat",
      rice: "rice",
      corn: "corn",
      maize: "maize",
      sugarcane: "sugarcane",
    };

    return cropMap[cropName.toLowerCase()] || "wheat"; // Default fallback to wheat
  };

  // Map section IDs to their recommended crops with fallback
  const sectionCropMap = useMemo(() => {
    const map: Record<string, CropKey> = {};
    let fallbackIndex = 0;

    if (recommendations) {
      Object.entries(recommendations).forEach(([sectionId, cropOptions]) => {
        if (Array.isArray(cropOptions) && cropOptions.length > 0) {
          // Use the first recommended crop (lowest risk)
          const recommendedCropName = cropOptions[0].crop;
          map[sectionId] = getCropMapping(recommendedCropName);
        } else {
          // Fallback: cycle through available crops
          map[sectionId] =
            FALLBACK_CROPS[fallbackIndex % FALLBACK_CROPS.length];
          fallbackIndex++;
        }
      });
    }

    return map;
  }, [recommendations]);

  // Header height: status bar + navigation bar
  const headerHeight = insets.top + (Platform.OS === "ios" ? 44 : 56);

  const loader = new SVGLoader();
  const data = loader.parse(svg);

  const viewBoxData = extractViewBox(svg);

  const { minX, minY, width, height } = viewBoxData ?? {
    minX: 0,
    minY: 0,
    width: 20,
    height: 10,
  };

  const maxSize = Math.max(width, height);

  const SVG_SCALE = 0.02;
  const FOV = 50;

  const cameraDistance = useMemo(() => {
    const maxDim = Math.max(width, height) * SVG_SCALE;
    const fovRad = (FOV * Math.PI) / 180;

    return maxDim / (2 * Math.tan(fovRad / 2));
  }, [width, height]);

  const cameraPosition: [number, number, number] = [
    0,
    cameraDistance,
    cameraDistance,
  ];

  const center = {
    x: minX + width / 2,
    y: minY + height / 2,
  };

  const meshes = useMemo(() => {
    return data.paths.flatMap((path) => {
      const id = path.userData?.node?.getAttribute?.("id");
      const shapes = path.toShapes(true);

      const color = new THREE.Color(getRandomSectionColor());

      return shapes.map((shape) => {
        const geometry = new THREE.ExtrudeGeometry(shape, {
          depth: 10,
          bevelEnabled: false,
        });

        geometry.translate(-center.x, -center.y, 0);

        return {
          id,
          geometry,
          material: new THREE.MeshStandardMaterial({ color }),
        };
      });
    });
  }, [center.x, center.y, data.paths]);

  if (!assetsLoaded) {
    return (
      <SafeAreaView style={styles.container}>
        <View
          style={{ flex: 1, justifyContent: "center", alignItems: "center" }}
        >
          <Text>Loading 3D assets…</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["left", "right", "bottom"]}>
      {selectedSectionId && selectedCrop && (
        <CropInfoCard crop={CROP_INFO[selectedCrop]} />
      )}
      <View style={{ flex: 1, paddingTop: headerHeight }}>
        <Canvas
          style={{
            flex: 1,
            height: Dimensions.get("window").height * 0.75,
          }}
          camera={{
            position: cameraPosition,
            fov: 50,
            near: 0.1,
            far: maxSize * 5,
          }}
          onCreated={({ camera }) => {
            cameraRef.current = camera as THREE.PerspectiveCamera;
          }}
          gl={{ stencil: true }}
        >
          <SceneReadyDetector onReady={() => setSceneReady(true)} />
          <CameraAnimation
            targetPosition={cameraPosition}
            startAnimation={sceneReady}
            duration={1200}
          />

          <ambientLight intensity={0.7} />
          <directionalLight position={[12, 15, 12]} intensity={1.5} />

          {/* Base soil */}
          <group scale={[0.02, 0.02, 0.02]} rotation={[Math.PI / 2, 0, 0]}>
            {meshes.map((m, i) => {
              // Get the crop from recommendations or use fallback
              const crop: CropKey =
                sectionCropMap[m.id] ||
                FALLBACK_CROPS[i % FALLBACK_CROPS.length];

              return (
                <CropBase
                  key={m.id}
                  id={m.id}
                  geometry={m.geometry}
                  material={m.material}
                  crop={crop}
                  isSelected={selectedSectionId === m.id}
                  onSelect={(sectionId) => handleSelect(sectionId, crop)}
                />
              );
            })}
          </group>
          <OrbitControls enableZoom={false} />
        </Canvas>
        <ZoomButtons cameraRef={cameraRef} />
      </View>
    </SafeAreaView>
  );
};

export default FarmPlanning;

const useStyles = () => {
  const colors = useTheme();

  const styles = StyleSheet.create({
    container: {
      backgroundColor: colors.background,
      flex: 1,
      // paddingHorizontal: SIZES.spacing.SPACING_28,
    },
    title: {
      fontSize: 32,
      fontWeight: "bold",
      marginBottom: 20,
    },
  });

  return styles;
};
