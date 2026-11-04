import { StyleSheet, Text, View, ScrollView, Pressable } from "react-native";
import React, { useEffect, useState } from "react";
import { useTheme } from "@/hooks/useTheme";
import { useLocalSearchParams, router } from "expo-router";
import { getScheme } from "@/lib/api/scheme/scheme.api";

type Scheme = {
  id: string;
  title: string;
  description: string;
  benefits: string;
  required_documents: string[];
};

const SAMPLE_REQUIRED_DOCUMENTS = {
  required_documents: [
    "Aadhaar Card",
    "Land Ownership / Lease Proof",
    "Bank Passbook",
    "Recent Farm Photo",
  ],
};

const SchemeForm = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const colors = useTheme();
  const styles = useStyles();
  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const load = async () => {
      if (!id) return;
      const data = await getScheme({ id });
      if (data) {
        setScheme(data);
        setLoading(false);
      }
    };
    // load();
  }, [id]);

  const requiredDocuments = scheme?.required_documents?.length
    ? scheme.required_documents
    : SAMPLE_REQUIRED_DOCUMENTS.required_documents;
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
    >
      {/* Scheme Title */}
      <Text style={[styles.title, { color: colors.text }]}>
        {scheme?.title || "Government Scheme"}
      </Text>

      {/* Description */}
      <Text style={[styles.description, { color: colors.textMuted }]}>
        {scheme?.description ||
          "This government scheme provides financial and technical support to farmers."}
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Benefits</Text>
        <Text style={styles.cardText}>
          {scheme?.benefits ||
            "Subsidy, financial aid, and access to agricultural resources."}
        </Text>
      </View>

      {/* Documents Section */}
      <View style={[styles.card, styles.warningCard]}>
        <Text style={styles.cardTitle}>Required Documents</Text>

        {requiredDocuments.map((doc, index) => (
          <Text key={index} style={styles.cardText}>
            • {doc}
          </Text>
        ))}

        <Text style={styles.note}>
          ⚠️ You will need to upload these documents to apply for this scheme.
        </Text>
      </View>
      {/* Apply Button */}
      <Pressable
        style={[styles.applyButton, { backgroundColor: colors.primary }]}
        onPress={() =>
          router.push({
            pathname: "/scheme/apply",
            params: { id },
          })
        }
      >
        <Text style={styles.applyText}>Apply Now</Text>
      </Pressable>
    </ScrollView>
  );
};

export default SchemeForm;

const useStyles = () => {
  const colors = useTheme();
  const styles = StyleSheet.create({
    container: {
      padding: 16,
      paddingBottom: 32,
    },
    title: {
      fontSize: 22,
      fontWeight: "700",
      marginBottom: 8,
    },
    description: {
      fontSize: 14,
      marginBottom: 16,
      lineHeight: 20,
    },
    card: {
      backgroundColor: "#fff",
      borderRadius: 12,
      padding: 14,
      marginBottom: 12,
      elevation: 2,
    },
    warningCard: {
      borderLeftWidth: 4,
      borderLeftColor: "#f59e0b",
    },
    cardTitle: {
      fontSize: 16,
      fontWeight: "600",
      marginBottom: 6,
    },
    cardText: {
      fontSize: 14,
      marginBottom: 4,
    },
    note: {
      marginTop: 8,
      fontSize: 13,
      color: "#92400e",
    },
    applyButton: {
      marginTop: 20,
      paddingVertical: 14,
      borderRadius: 10,
      alignItems: "center",
    },
    applyText: {
      color: colors.text,
      fontSize: 16,
      fontWeight: "700",
    },
  });
  return styles;
};
