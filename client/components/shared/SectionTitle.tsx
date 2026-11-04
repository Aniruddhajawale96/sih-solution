import { StyleSheet, Text, TextStyle, View, ViewStyle } from "react-native";
import React, { useMemo } from "react";
import PressableOpacity from "./PressableOpacity";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import SIZES from "@/constants/sizes";
import { useTheme } from "@/hooks/useTheme";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";

interface SectionTitleProps {
  title: string;
  ctaTitle?: string;
  ctaOnPress?: () => void;
  containerStyle?: ViewStyle;
  titleStyle?: TextStyle;
  ctaStyle?: TextStyle;
}

const SectionTitle = ({
  title,
  ctaTitle,
  ctaOnPress,
  containerStyle,
  ctaStyle,
  titleStyle,
}: SectionTitleProps) => {
  const colors = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        sectionDescription: {
          color: colors.anchor,
          fontWeight: FONT_WEIGHTS.semibold,
        },
        sectionTitleContainer: {
          width: "100%",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
          paddingHorizontal: SIZES.spacing.SPACING_4,
          marginVertical: SIZES.spacing.SPACING_8,
        },
        sectionTitle: {
          fontSize: FONT_SIZES.xl,
          fontWeight: FONT_WEIGHTS.semibold,
        },
      }),
    [colors]
  );

  return (
    <View style={[styles.sectionTitleContainer, containerStyle]}>
      <Text style={[styles.sectionTitle, titleStyle]}>{title}</Text>
      {ctaTitle && (
        <View>
          <PressableOpacity
            hitSlop={10}
            style={{
              flexDirection: "row",
              justifyContent: "center",
              alignItems: "center",
              gap: SIZES.spacing.SPACING_12,
            }}
            onPress={ctaOnPress}
          >
            <Text style={[styles.sectionDescription, ctaStyle]}>
              {ctaTitle}
            </Text>
            <FontAwesome
              name="angle-right"
              size={SIZES.icon.MD}
              color={colors.anchor}
            />
          </PressableOpacity>
        </View>
      )}
    </View>
  );
};

export default SectionTitle;
