import { StyleSheet, Text, View, Pressable, Alert } from "react-native";
import React, { useState } from "react";
import * as DocumentPicker from "expo-document-picker";
import { router, useLocalSearchParams } from "expo-router";
import { useTheme } from "@/hooks/useTheme";
import { submitSchemeApplication } from "@/lib/api/scheme/scheme.api";

interface ZipFile {
  uri: string;
  name: string;
  size?: number;
  type: string;
}

const Apply = () => {
  const colors = useTheme();
  const { id: schemeId } = useLocalSearchParams<{ id: string }>();

  const [zipFile, setZipFile] = useState<ZipFile | null>(null);
  const [loading, setLoading] = useState(false);

  // 👉 Hardcoded farmer ID for now
  const FARMER_ID = "679f5a72a78c62a0a1cf2b82"; // Replace with your actual farmer ID

  const pickZipFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "application/zip",
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets[0]) {
        setZipFile(result.assets[0]);
      }
    } catch (error) {
      Alert.alert("Error", "Failed to pick file");
    }
  };

  const submitApplication = async () => {
    if (!schemeId) {
      Alert.alert("Error", "Scheme ID not found");
      return;
    }

    if (!zipFile) {
      Alert.alert("Missing File", "Please upload a ZIP file first");
      return;
    }

    try {
      setLoading(true);

      await submitSchemeApplication({
        farmerId: FARMER_ID,
        schemeId,
        zipFile: {
          uri: zipFile.uri,
          name: zipFile.name,
          type: "application/zip",
        },
      });

      Alert.alert(
        "Success",
        "Scheme application submitted successfully",
        [
          {
            text: "OK",
            onPress: () => {
              setZipFile(null);
              router.navigate("/(main)/(schemes)");
            },
          },
        ]
      );
    } catch (error: any) {
      const errorMessage = error?.response?.data?.message ||
        error?.response?.data?.detail ||
        "Submission failed";
      Alert.alert("Error", errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text }]}>
        Apply for Scheme
      </Text>
      <Text style={styles.info}>
        Upload a single ZIP file containing all required documents.
      </Text>

      {/* Upload ZIP */}
      <Pressable
        onPress={pickZipFile}
        style={[
          styles.uploadButton,
          { borderColor: colors.primary },
          loading && styles.disabled,
        ]}
        disabled={loading}
      >
        <Text style={[styles.uploadText, { color: colors.primary }]}>
          {zipFile ? "Change ZIP File" : "Upload ZIP File"}
        </Text>
      </Pressable>

      {/* Selected File Info */}
      {zipFile && (
        <View style={styles.fileInfo}>
          <Text style={styles.fileName}>{zipFile.name}</Text>
          {zipFile.size && (
            <Text style={styles.fileSize}>
              {(zipFile.size / 1024).toFixed(2)} KB
            </Text>
          )}
        </View>
      )}

      {/* Submit */}
      <Pressable
        onPress={submitApplication}
        style={[
          styles.submitButton,
          { backgroundColor: colors.primary },
          (!zipFile || loading) && styles.disabled,
        ]}
        disabled={!zipFile || loading}
      >
        <Text style={styles.submitText}>
          {loading ? "Submitting..." : "Submit Application"}
        </Text>
      </Pressable>

      <Text style={styles.note}>
        ⚠️ Make sure the ZIP contains all required documents before submitting.
      </Text>
    </View>
  );
};

export default Apply;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 6,
  },
  info: {
    fontSize: 14,
    color: "#6b7280",
    marginBottom: 16,
  },
  uploadButton: {
    borderWidth: 1.5,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
  },
  uploadText: {
    fontSize: 16,
    fontWeight: "600",
  },
  fileInfo: {
    marginTop: 12,
    padding: 12,
    borderRadius: 8,
    backgroundColor: "#f3f4f6",
  },
  fileName: {
    fontSize: 14,
    fontWeight: "600",
  },
  fileSize: {
    fontSize: 12,
    color: "#6b7280",
    marginTop: 2,
  },
  submitButton: {
    marginTop: 20,
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  submitText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.5,
  },
  note: {
    marginTop: 16,
    fontSize: 13,
    color: "#92400e",
  },
});