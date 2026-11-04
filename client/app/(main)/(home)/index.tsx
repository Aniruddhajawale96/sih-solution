import { ScrollView, StyleSheet, Text, View } from "react-native";
import React, { useEffect, useState } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "@/hooks/useTheme";
import SIZES from "@/constants/sizes";
import { stringsKeys } from "@/constants/strings";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";
import useAppStore from "@/store";
import SectionTitle from "@/components/shared/SectionTitle";
import ScreenTitle from "@/components/shared/ScreenTitle";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import ActionCard from "@/components/ActionCard";
import { images } from "@/constants/images";
import { MOCK_WEATHER_ALERTS, WeatherAlert } from "@/mocks/weatherAlerts";
import AlertCard from "@/components/shared/AlertCard";
import Animated, { FadeIn, FadeInDown, ZoomIn } from "react-native-reanimated";
import { getWorstWeatherNext300Days } from "@/lib/api/weather/getWorstWeatherData";
import { getWeatherAlerts } from "@/lib/api/weather/getForecast";

const Home = () => {
  const styles = useStyles();
  const { t } = useTranslation();

  const user = useAppStore((state) => state.user);
  const welcomeTitle = `${t(stringsKeys.dashboard.welcomeMessage)} ${user.name},`;

  const [weatherAlerts, setWeatherAlerts] =
    useState<WeatherAlert[]>(MOCK_WEATHER_ALERTS);

  const removeAlert = (id: string) => {
    setWeatherAlerts((prev) => prev.filter((alert) => alert.id !== id));
  };

  useEffect(() => {
    const load = async () => {
      const data = await getWeatherAlerts({ latitude: 62.0, longitude: 129.7 });
      console.log(data);
      setWeatherAlerts(data);
    };
    load();
  }, []);

  return (
    <SafeAreaView style={styles.appContainer}>
      <Animated.View entering={ZoomIn.duration(500)} style={styles.avatar} />
      <Animated.View entering={FadeInDown.duration(500).delay(100)}>
        <ScreenTitle
          title={welcomeTitle}
          description={t(stringsKeys.dashboard.welcomeDescription)}
        />
      </Animated.View>

      <View style={styles.actionContainer}>
        <ActionCard
          onCta={() =>
            router.navigate("/(main)/(home)/farmPlanning/DetailScreen")
          }
          style={{ height: 300 }}
          imageUri={images.planFarm}
        >
          <Text style={styles.actionTitle}>
            {t(stringsKeys.dashboard.actions.planFarmTitle)}
          </Text>
          <Text style={styles.actionSubtitle}>
            {t(stringsKeys.dashboard.actions.planFarmDecription)}
          </Text>
        </ActionCard>
      </View>
      {/* temp for map check */}
      {/* <TouchableOpacity
          style={{
            backgroundColor: "#007BFF",
            padding: 10,
            borderRadius: 5,
            marginVertical: 20,
            alignItems: "center",
            }}
            onPress={() => router.navigate("/farmPlanning/farmMap3D")}
            >
            <Text style={{ color: "white", fontWeight: "bold" }}>
            Go to 3D Map Screen
            </Text>
            </TouchableOpacity> */}
      <SectionTitle title={t("upcoming_alerts")} />
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={{ gap: SIZES.spacing.SPACING_12 }}>
          {weatherAlerts.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyTitle}>🌤️ No weather alerts</Text>
              <Text style={styles.emptyMessage}>
                Weather looks good for the coming days.
              </Text>
            </View>
          ) : (
            weatherAlerts.map((alert, index) => (
              <Animated.View
                key={alert.id}
                entering={FadeInDown.duration(400).delay(index * 120)}
              >
                <AlertCard
                  title={alert.title}
                  message={alert.message}
                  severity={alert.severity}
                  onDismiss={() => removeAlert(alert.id)}
                />
              </Animated.View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

export default Home;

const useStyles = () => {
  const colors = useTheme();

  const AVATAR_SIZE = SIZES.image_sizes.AVATAR_MD;

  const styles = StyleSheet.create({
    appContainer: {
      backgroundColor: colors.background,
      flex: 1,
      paddingHorizontal: SIZES.spacing.SPACING_28,
      overflow: "visible",
    },
    actionContainer: {
      justifyContent: "center",
      alignItems: "center",
      gap: SIZES.spacing.SPACING_20,
      marginVertical: SIZES.spacing.SPACING_28,
    },
    avatar: {
      height: AVATAR_SIZE,
      width: AVATAR_SIZE,
      backgroundColor: colors.primary,
      alignSelf: "flex-end",
      borderRadius: SIZES.radius.FULL,
    },
    actionTitle: {
      fontSize: FONT_SIZES["2xl"],
      fontWeight: FONT_WEIGHTS.bold,
      color: "#fff",
      marginTop: SIZES.spacing.SPACING_40 * 4.85,
    },
    actionSubtitle: {
      fontSize: FONT_SIZES.md * 0.9,
      fontWeight: FONT_WEIGHTS.regular,
      color: colors.disabled,
    },
    emptyState: {
      marginTop: SIZES.spacing.SPACING_20,
      paddingVertical: SIZES.spacing.SPACING_24,
      paddingHorizontal: SIZES.spacing.SPACING_16,
      borderRadius: SIZES.radius.MD,
      backgroundColor: colors.cardBackground,
      alignItems: "center",
      gap: 6,
    },

    emptyTitle: {
      fontSize: FONT_SIZES.lg,
      fontWeight: FONT_WEIGHTS.semibold,
      color: colors.text,
    },

    emptyMessage: {
      fontSize: FONT_SIZES.sm,
      color: colors.textMuted,
      textAlign: "center",
    },
  });

  return styles;
};
