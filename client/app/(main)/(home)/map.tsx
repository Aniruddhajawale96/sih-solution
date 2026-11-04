import {
  Dimensions,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "@/hooks/useTheme";
import SIZES from "@/constants/sizes";
import { stringsKeys } from "@/constants/strings";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";
import GroupCard from "@/components/shared/GroupCard";
import useAppStore from "@/store";
import SectionTitle from "@/components/shared/SectionTitle";
import ScreenTitle from "@/components/shared/ScreenTitle";
import { router } from "expo-router";
import { useTranslation } from "react-i18next";
import ActionCard from "@/components/ActionCard";
import { images } from "@/constants/images";

const Home = () => {
  const styles = useStyles();
  const { t } = useTranslation();

  const user = useAppStore((state) => state.user);
  const welcomeTitle = `${t(stringsKeys.dashboard.welcomeMessage)} ${user.name},`;

  return (
    <SafeAreaView style={styles.appContainer}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.avatar}>{/* image */}</View>
        <ScreenTitle
          title={welcomeTitle}
          description={t(stringsKeys.dashboard.welcomeDescription)}
        />
        <View style={styles.actionContainer}>
          <ActionCard
            onCta={() =>
              router.navigate("/(main)/(home)/farmPlanning/farmMap3D")
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
        <TouchableOpacity
          style={{
            backgroundColor: "#007BFF",
            padding: 10,
            borderRadius: 5,
            marginVertical: 20,
            alignItems: "center",
          }}
          onPress={() => router.navigate("/farmPlanning/farmMap")}
        >
          <Text style={{ color: "white", fontWeight: "bold" }}>
            Go to Map Screen
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={{
            backgroundColor: "#007BFF",
            padding: 10,
            borderRadius: 5,
            marginVertical: 20,
            alignItems: "center",
          }}
          onPress={() => router.navigate("/test")}
        >
          <Text style={{ color: "white", fontWeight: "bold" }}>
            Go to weather api test screen
          </Text>
        </TouchableOpacity>
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
  });

  return styles;
};
