import React, { useState } from "react";
import {
    View,
    Text,
    Pressable,
    Image,
    StyleSheet,
    Alert,
    ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import { useTheme } from "@/hooks/useTheme";
import { checkFarmVisit } from "@/lib/api/farm/farmVisit";
import { Ionicons } from "@expo/vector-icons";

const TEST_BOUNDARY = [
    { latitude: 19.0, longitude: 72.0 },
    { latitude: 19.0, longitude: 72.001 },
    { latitude: 19.001, longitude: 72.001 },
    { latitude: 19.001, longitude: 72.0 },
];

export default function FarmValidationTest() {
    const colors = useTheme();
    const styles = createStyles(colors);

    const [images, setImages] = useState<string[]>([]);
    const [statusMsg, setStatusMsg] = useState("");
    const [inside, setInside] = useState<boolean | null>(null);
    const [canSubmit, setCanSubmit] = useState(false);

    const captureImage = async () => {
        if (images.length >= 5) {
            Alert.alert("Limit reached", "Maximum 5 images allowed");
            return;
        }

        const res = await ImagePicker.launchCameraAsync({
            quality: 0.5,
            base64: false,
        });

        if (!res.canceled) {
            setImages((prev) => [...prev, res.assets[0].uri]);
        }
    };

    const removeImage = (index: number) => {
        setImages((prev) => prev.filter((_, i) => i !== index));
    };

    const validateLocation = async () => {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== "granted") {
            Alert.alert("Permission denied", "Location permission required");
            return;
        }

        const loc = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.High,
        });

        try {
            const data = await checkFarmVisit({
                boundary: TEST_BOUNDARY,
                user_location: {
                    latitude: loc.coords.latitude,
                    longitude: loc.coords.longitude,
                },
                image_count: images.length,
                gps_accuracy: loc.coords.accuracy ?? 20,
            });

            setInside(data.inside_boundary);
            setCanSubmit(data.can_submit);
            setStatusMsg(data.message);
        } catch (error: any) {
            Alert.alert("Error", "Failed to validate farm visit");
        }
    };

    const submitVisit = () => {
        Alert.alert("Submitted", "Farm visit submitted successfully");
    };

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView showsVerticalScrollIndicator={false}>
                <Text style={styles.title}>Farm Visit Validation</Text>

                {/* Capture Card */}
                <View style={styles.card}>
                    <Text style={styles.cardTitle}>Capture Farm Images</Text>

                    <Pressable style={styles.captureBtn} onPress={captureImage}>
                        <Ionicons name="camera" size={18} color="#fff" />
                        <Text style={styles.captureText}>
                            Capture Image ({images.length}/5)
                        </Text>
                    </Pressable>

                    {/* Image Grid */}
                    <View style={styles.imageGrid}>
                        {images.map((uri, i) => (
                            <View key={i} style={styles.imageWrapper}>
                                <Image source={{ uri }} style={styles.image} />
                                <Pressable
                                    style={styles.deleteBtn}
                                    onPress={() => removeImage(i)}
                                >
                                    <Ionicons name="close" size={14} color="#fff" />
                                </Pressable>
                            </View>
                        ))}
                    </View>
                </View>

                {/* Validation Card */}
                <View style={styles.card}>
                    <Text style={styles.cardTitle}>Location Validation</Text>

                    <Pressable style={styles.validateBtn} onPress={validateLocation}>
                        <Ionicons name="location" size={18} color="#fff" />
                        <Text style={styles.validateText}>Validate Location</Text>
                    </Pressable>

                    {statusMsg !== "" && (
                        <View
                            style={[
                                styles.statusBadge,
                                { backgroundColor: inside ? "#16a34a" : "#dc2626" },
                            ]}
                        >
                            <Text style={styles.statusText}>{statusMsg}</Text>
                        </View>
                    )}
                </View>

                {/* Submit Button */}
                <Pressable
                    style={[styles.submitBtn, { opacity: canSubmit ? 1 : 0.4 }]}
                    disabled={!canSubmit}
                    onPress={submitVisit}
                >
                    <Text style={styles.submitText}>Submit Visit</Text>
                </Pressable>
            </ScrollView>
        </SafeAreaView>
    );
}

const createStyles = (colors: any) =>
    StyleSheet.create({
        container: {
            flex: 1,
            backgroundColor: colors.background,
            padding: 20,
        },

        title: {
            fontSize: 26,
            fontWeight: "800",
            marginBottom: 18,
            color: colors.text,
        },

        card: {
            backgroundColor: colors.card ?? "#fff",
            borderRadius: 18,
            padding: 16,
            marginBottom: 16,
            elevation: 4,
            shadowColor: "#000",
            shadowOpacity: 0.08,
            shadowRadius: 10,
            shadowOffset: { width: 0, height: 4 },
        },

        cardTitle: {
            fontSize: 16,
            fontWeight: "700",
            marginBottom: 12,
            color: colors.text,
        },

        captureBtn: {
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            backgroundColor: colors.primary,
            padding: 14,
            borderRadius: 12,
        },

        captureText: {
            color: "#fff",
            fontWeight: "600",
        },

        imageGrid: {
            flexDirection: "row",
            flexWrap: "wrap",
            gap: 10,
            marginTop: 12,
        },

        imageWrapper: {
            position: "relative",
        },

        image: {
            width: 80,
            height: 80,
            borderRadius: 12,
        },

        deleteBtn: {
            position: "absolute",
            top: -6,
            right: -6,
            backgroundColor: "#ef4444",
            borderRadius: 20,
            padding: 4,
        },

        validateBtn: {
            flexDirection: "row",
            justifyContent: "center",
            alignItems: "center",
            gap: 8,
            backgroundColor: "#2563eb",
            padding: 14,
            borderRadius: 12,
        },

        validateText: {
            color: "#fff",
            fontWeight: "600",
        },

        statusBadge: {
            marginTop: 14,
            paddingVertical: 8,
            paddingHorizontal: 12,
            borderRadius: 999,
            alignSelf: "center",
        },

        statusText: {
            color: "#fff",
            fontWeight: "700",
            fontSize: 13,
        },

        submitBtn: {
            backgroundColor: "#16a34a",
            padding: 16,
            borderRadius: 16,
            alignItems: "center",
            marginTop: 6,
            marginBottom: 30,
        },

        submitText: {
            color: "#fff",
            fontSize: 16,
            fontWeight: "700",
        },
    });
