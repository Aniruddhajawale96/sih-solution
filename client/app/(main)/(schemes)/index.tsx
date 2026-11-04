import React, { useCallback, useState } from "react";
import { View, Text, FlatList, Pressable, StyleSheet } from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";
import { useTheme } from "@/hooks/useTheme";
import SIZES from "@/constants/sizes";
import { getSchemes, SchemeShow } from "@/lib/api/scheme/scheme.api";
import SectionTitle from "@/components/shared/SectionTitle";
import { useTranslation } from "react-i18next";

export default function FakeSchemesScreen() {
  const router = useRouter();
  const styles = useStyles();

  const [schemes, setSchemes] = useState<SchemeShow[]>([]);
  const [loading, setLoading] = useState(false);

  /**TEMP farmer id (later from JWT auth context) */
  const farmerId = "CURRENT_LOGGED_IN_ID";

  const { t } = useTranslation();
  const renderItem = ({ item }: any) => {
    return (
      <Pressable
        style={styles.card}
        onPress={() =>
          router.navigate({
            pathname: "/scheme-form",
            params: { id: item.id },
          })
        }
      >
        <Text style={styles.title}>{item.title}</Text>
        <Text style={styles.desc}>{item.description}</Text>

        <View style={styles.badge}>
          <Text style={styles.badgeText}>Eligible in {item.location}</Text>
        </View>

        <View style={styles.applyContainer}>
          <Text style={styles.apply}>Tap to Apply →</Text>
        </View>
      </Pressable>
    );
  };

  useFocusEffect(
    useCallback(() => {
      let isActive = true;

      const loadSchemes = async () => {
        try {
          setLoading(true);

          const res = await fetch(
            `http://192.168.137.1:8000/api/v1/farmer-schemes/`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                farmer_id: "69854219499c626019c15748",
              }),
            }
          );

          const json = await res.json();

          if (!res.ok) throw new Error(json.detail || "Failed to load schemes");

          // map backend → UI type
          const mapped = json.schemes.map((s: any) => ({
            id: s._id,
            title: s.title,
            description: s.description,
            location: s.location,
          }));

          if (isActive) setSchemes(mapped);
        } catch (err) {
          console.log("Failed to load schemes", err);
        } finally {
          if (isActive) setLoading(false);
        }
      };

      // load every time screen focuses
      loadSchemes();

      return () => {
        isActive = false;
      };
    }, [])
  );


  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.header}>{t(`Schemes for You`)}</Text>

      <FlatList
        data={schemes}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ flexGrow: 1, paddingBottom: 20 }}
        ListEmptyComponent={
          <View
            style={{
              flex: 1,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <SectionTitle title={t("Nothing to display here")} />
          </View>
        }
      />
    </SafeAreaView>
  );
}

const useStyles = () => {
  const colors = useTheme();

  return StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: "#F5F7FB",
      padding: 16,
    },
    header: {
      fontSize: 24,
      fontWeight: "800",
      marginBottom: 16,
      color: "#111",
    },
    card: {
      backgroundColor: "#fff",
      borderRadius: 16,
      padding: 16,
      marginBottom: 12,
      shadowColor: "#000",
      shadowOpacity: 0.08,
      shadowRadius: 10,
      shadowOffset: { width: 0, height: 4 },
      elevation: 3,
    },
    title: {
      fontSize: 18,
      fontWeight: "700",
      marginBottom: 6,
      color: "#111",
    },
    desc: {
      fontSize: 14,
      color: "#555",
      marginBottom: 10,
    },
    badge: {
      alignSelf: "flex-start",
      backgroundColor: "#DCFCE7",
      paddingHorizontal: 10,
      paddingVertical: 4,
      borderRadius: 999,
      marginBottom: 10,
    },
    badgeText: {
      color: "#166534",
      fontWeight: "600",
      fontSize: 12,
    },
    applyContainer: {
      alignSelf: "flex-start",
      backgroundColor: colors.warning,
      paddingHorizontal: SIZES.spacing.SPACING_16,
      paddingVertical: SIZES.spacing.SPACING_8,
      borderRadius: 999,
    },
    apply: {
      color: colors.warningDark,
      fontWeight: FONT_WEIGHTS.semibold,
      fontSize: FONT_SIZES.base,
    },
  });
};
