import {
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
  ScrollView,
} from "react-native";
import React, { useEffect } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";
import Animated, {
  FadeInDown,
  FadeInUp,
  ZoomIn,
  SlideInRight,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
  withDelay,
  withSequence,
  FadeInRight,
} from "react-native-reanimated";

import LanguageSelector from "@/components/shared/LangSelector";
import { useTheme } from "@/hooks/useTheme";
import { supabase } from "@/lib/services/supabase";
import ScreenTitle from "@/components/shared/ScreenTitle";
import GroupCard from "@/components/shared/GroupCard";
import { AVATAR_URL } from "@/constants/defaults";
import SIZES from "@/constants/sizes";
import Title from "@/components/shared/Title";
import useAppStore from "@/store";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

const ProfileScreen = () => {
  const styles = useStyles();
  const colors = useTheme();
  const { t } = useTranslation();
  const user = useAppStore((state) => state.user);

  // Shared values for custom animations
  const avatarScale = useSharedValue(0);
  const glowOpacity = useSharedValue(0);

  useEffect(() => {
    // Avatar pop animation
    avatarScale.value = withDelay(
      300,
      withSpring(1, {
        damping: 8,
        stiffness: 100,
      }),
    );

    // Glow pulse animation
    glowOpacity.value = withDelay(
      500,
      withSequence(
        withTiming(0.6, { duration: 800 }),
        withTiming(0.3, { duration: 800 }),
      ),
    );
  }, []);

  const avatarAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: avatarScale.value }],
  }));

  const glowAnimatedStyle = useAnimatedStyle(() => ({
    opacity: glowOpacity.value,
  }));

  async function onSignOutButtonPress() {
    const { error } = await supabase.auth.signOut();
    if (error) console.error("Error signing out:", error);
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        <ScreenTitle title={t("profile_title")} />

        {/* Header Card */}
        <Animated.View
          entering={FadeInDown.delay(100).duration(600).springify()}
          style={styles.headerCard}
        >
          <LinearGradient
            colors={[colors.primary + "15", colors.primary + "05"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.gradientBackground}
          />

          {/* Avatar */}
          <View style={styles.avatarSection}>
            <Animated.View style={[styles.avatarWrapper, avatarAnimatedStyle]}>
              <Animated.View style={[styles.avatarGlow, glowAnimatedStyle]} />
              <Image source={{ uri: AVATAR_URL }} style={styles.avatar} />
              <Animated.View
                entering={ZoomIn.delay(800).duration(400).springify()}
                style={styles.statusBadge}
              >
                <View style={styles.statusDot} />
              </Animated.View>
            </Animated.View>

            <Animated.View entering={FadeInUp.delay(400).duration(500)}>
              <Title>{user?.name || t("profile_user_default_name")}</Title>
            </Animated.View>

            <Animated.View
              entering={FadeInUp.delay(500).duration(500)}
              style={styles.badgeContainer}
            >
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{t("profile_role_farmer")}</Text>
              </View>
              <View style={[styles.badge, styles.badgeSecondary]}>
                <Text style={styles.badgeTextSecondary}>
                  {t("profile_role_app_user")}
                </Text>
              </View>
            </Animated.View>
          </View>

          {/* Stats */}
          <Animated.View
            entering={FadeInUp.delay(600).duration(600)}
            style={styles.statsRow}
          >
            <Animated.View
              entering={FadeInUp.delay(700).duration(400)}
              style={styles.statItem}
            >
              <Text style={styles.statValue}>12</Text>
              <Text style={styles.statLabel}>{t("profile_stats_farms")}</Text>
            </Animated.View>

            <View style={styles.statDivider} />

            <Animated.View
              entering={FadeInUp.delay(800).duration(400)}
              style={styles.statItem}
            >
              <Text style={styles.statValue}>24</Text>
              <Text style={styles.statLabel}>{t("profile_stats_crops")}</Text>
            </Animated.View>

            <View style={styles.statDivider} />

            <Animated.View
              entering={FadeInUp.delay(900).duration(400)}
              style={styles.statItem}
            >
              <Text style={styles.statValue}>89%</Text>
              <Text style={styles.statLabel}>{t("profile_stats_success")}</Text>
            </Animated.View>
          </Animated.View>
        </Animated.View>

        {/* Settings */}
        <Animated.View
          entering={FadeInDown.delay(1000).duration(500).springify()}
          style={styles.section}
        >
          <Text style={styles.sectionTitle}>
            {t("profile_section_settings")}
          </Text>
          <View style={styles.settingsCard}>
            <LanguageSelector />
          </View>
        </Animated.View>

        {/* Quick Actions */}
        <Animated.View
          entering={FadeInDown.delay(1100).duration(500).springify()}
          style={styles.section}
        >
          <Text style={styles.sectionTitle}>
            {t("profile_section_quick_actions")}
          </Text>

          <AnimatedPressable
            entering={SlideInRight.delay(1200).duration(500).springify()}
            style={({ pressed }) => [
              styles.actionButton,
              styles.primaryAction,
              pressed && styles.pressed,
            ]}
            onPress={() => router.navigate("/farmPlanning/farmMap3D")}
          >
            <>
              <LinearGradient
                colors={[colors.primary, colors.primary + "DD"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.buttonGradient}
              />
              <View style={styles.buttonContent}>
                <View style={styles.iconCircle}>
                  <Text style={styles.iconText}>🗺️</Text>
                </View>
                <View style={styles.buttonTextContainer}>
                  <Text style={styles.buttonTitle}>
                    {t("profile_action_view_farm_title")}
                  </Text>
                  <Text style={styles.buttonSubtitle}>
                    {t("profile_action_view_farm_subtitle")}
                  </Text>
                </View>
                <Text style={styles.chevron}>›</Text>
              </View>
            </>
          </AnimatedPressable>

          <Animated.View entering={FadeInDown.delay(1300).duration(500)}>
            <GroupCard>
              <View style={styles.menuItems}>
                <AnimatedPressable
                  entering={FadeInRight.delay(1400).duration(400)}
                  style={styles.menuItem}
                >
                  <Text style={styles.menuIcon}>👤</Text>
                  <Text style={styles.menuText}>
                    {t("profile_action_edit_profile")}
                  </Text>
                  <Text style={styles.menuChevron}>›</Text>
                </AnimatedPressable>

                <View style={styles.menuDivider} />

                <AnimatedPressable
                  entering={FadeInRight.delay(1500).duration(400)}
                  style={styles.menuItem}
                >
                  <Text style={styles.menuIcon}>🔔</Text>
                  <Text style={styles.menuText}>
                    {t("profile_action_notifications")}
                  </Text>
                  <Text style={styles.menuChevron}>›</Text>
                </AnimatedPressable>

                <View style={styles.menuDivider} />

                <AnimatedPressable
                  entering={FadeInRight.delay(1600).duration(400)}
                  style={styles.menuItem}
                >
                  <Text style={styles.menuIcon}>🔒</Text>
                  <Text style={styles.menuText}>
                    {t("profile_action_privacy_security")}
                  </Text>
                  <Text style={styles.menuChevron}>›</Text>
                </AnimatedPressable>
              </View>
            </GroupCard>
          </Animated.View>
        </Animated.View>

        <View style={styles.bottomSpacer} />
      </ScrollView>
    </SafeAreaView>
  );
};

export default ProfileScreen;

const useStyles = () => {
  const colors = useTheme();

  return StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    scrollContent: {
      paddingHorizontal: SIZES.spacing.SPACING_20,
    },
    headerCard: {
      backgroundColor: colors.cardBackground,
      borderRadius: 24,
      overflow: "hidden",
      marginTop: SIZES.spacing.SPACING_16,
      shadowColor: "#000",
      shadowOpacity: 0.1,
      shadowRadius: 20,
      shadowOffset: { width: 0, height: 4 },
      elevation: 8,
    },
    gradientBackground: {
      position: "absolute",
      top: 0,
      left: 0,
      right: 0,
      height: 200,
    },
    avatarSection: {
      alignItems: "center",
      paddingTop: 32,
      paddingBottom: 24,
    },
    avatarWrapper: {
      position: "relative",
      marginBottom: 16,
    },
    avatarGlow: {
      position: "absolute",
      top: -8,
      left: -8,
      right: -8,
      bottom: -8,
      borderRadius: 68,
      backgroundColor: colors.primary + "20",
    },
    avatar: {
      width: 120,
      height: 120,
      borderRadius: 60,
      borderWidth: 4,
      borderColor: colors.cardBackground,
    },
    statusBadge: {
      position: "absolute",
      bottom: 4,
      right: 4,
      backgroundColor: colors.cardBackground,
      borderRadius: 12,
      padding: 3,
      shadowColor: "#000",
      shadowOpacity: 0.2,
      shadowRadius: 4,
      elevation: 3,
    },
    statusDot: {
      width: 14,
      height: 14,
      borderRadius: 7,
      backgroundColor: "#4CAF50",
    },
    userName: {
      fontSize: 26,
      fontWeight: "700",
      color: colors.text,
      marginBottom: 8,
    },
    badgeContainer: {
      flexDirection: "row",
      gap: 8,
      marginTop: 4,
    },
    badge: {
      backgroundColor: colors.primary + "15",
      paddingHorizontal: 14,
      paddingVertical: 6,
      borderRadius: 20,
      borderWidth: 1,
      borderColor: colors.primary + "30",
    },
    badgeText: {
      color: colors.primary,
      fontSize: 13,
      fontWeight: "600",
    },
    badgeSecondary: {
      backgroundColor: colors.textMuted + "10",
      borderColor: colors.textMuted + "20",
    },
    badgeTextSecondary: {
      color: colors.textMuted,
      fontSize: 13,
      fontWeight: "500",
    },
    statsRow: {
      flexDirection: "row",
      paddingHorizontal: 24,
      paddingVertical: 20,
      backgroundColor: colors.background + "40",
      borderTopWidth: 1,
      borderTopColor: colors.border + "30",
    },
    statItem: {
      flex: 1,
      alignItems: "center",
    },
    statValue: {
      fontSize: 22,
      fontWeight: "700",
      color: colors.text,
      marginBottom: 4,
    },
    statLabel: {
      fontSize: 12,
      color: colors.textMuted,
      fontWeight: "500",
    },
    statDivider: {
      width: 1,
      backgroundColor: colors.border + "40",
      marginHorizontal: 8,
    },
    section: {
      marginTop: 24,
      gap: 12,
    },
    sectionTitle: {
      fontSize: 18,
      fontWeight: "700",
      color: colors.text,
      marginLeft: 4,
    },
    settingsCard: {
      backgroundColor: colors.cardBackground,
      borderRadius: 16,
      padding: 16,
      shadowColor: "#000",
      shadowOpacity: 0.06,
      shadowRadius: 12,
      elevation: 3,
    },
    actionButton: {
      borderRadius: SIZES.radius.MD,
      overflow: "hidden",
      marginBottom: 16,
      shadowColor: "#000",
      shadowOpacity: 0.15,
      shadowRadius: 16,
      shadowOffset: { width: 0, height: 4 },
      elevation: 6,
    },
    primaryAction: {
      height: 88,
    },
    buttonGradient: {
      position: "absolute",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
    },
    buttonContent: {
      flexDirection: "row",
      alignItems: "center",
      padding: 20,
      gap: 16,
    },
    iconCircle: {
      width: 48,
      height: 48,
      borderRadius: 24,
      backgroundColor: "rgba(255, 255, 255, 0.2)",
      alignItems: "center",
      justifyContent: "center",
    },
    iconText: {
      fontSize: 24,
    },
    buttonTextContainer: {
      flex: 1,
    },
    buttonTitle: {
      color: "#fff",
      fontSize: 18,
      fontWeight: "700",
      marginBottom: 2,
    },
    buttonSubtitle: {
      color: "rgba(255, 255, 255, 0.8)",
      fontSize: 13,
      fontWeight: "500",
    },
    chevron: {
      color: "#fff",
      fontSize: 32,
      fontWeight: "300",
    },
    menuItems: {
      gap: 0,
    },
    menuItem: {
      flexDirection: "row",
      alignItems: "center",
      paddingVertical: 14,
      gap: 12,
      borderRadius: SIZES.radius.MD,
    },
    menuIcon: {
      fontSize: 20,
      width: 28,
    },
    menuText: {
      flex: 1,
      fontSize: 15,
      color: colors.text,
      fontWeight: "500",
    },
    menuChevron: {
      fontSize: 20,
      color: colors.textMuted,
      fontWeight: "300",
    },
    menuDivider: {
      height: 1,
      backgroundColor: colors.border + "30",
      marginLeft: 40,
    },
    logoutButton: {
      flexDirection: "row",
      backgroundColor: colors.error + "10",
      paddingVertical: 16,
      borderRadius: 16,
      alignItems: "center",
      justifyContent: "center",
      marginTop: 24,
      gap: 10,
      borderWidth: 1,
      borderColor: colors.error + "20",
    },
    logoutIcon: {
      fontSize: 20,
    },
    logoutText: {
      color: colors.error,
      fontSize: 16,
      fontWeight: "600",
    },
    pressed: {
      opacity: 0.85,
      transform: [{ scale: 0.98 }],
    },
    bottomSpacer: {
      height: 24,
    },
  });
};
