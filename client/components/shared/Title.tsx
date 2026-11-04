import { StyleSheet, Text, TextStyle, View, ViewStyle } from "react-native";
import React from "react";
import { useTheme } from "@/hooks/useTheme";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";

interface SectionTitleProps {
  children: string;
}

const Title: React.FC<SectionTitleProps> = ({ children }) => {
  const styles = useStyles();
  return <Text style={[styles.title]}>{children}</Text>;
};

export default Title;

const useStyles = () => {
  const colors = useTheme();

  const styles = StyleSheet.create({
    title: {
      fontSize: FONT_SIZES["3xl"],
      fontWeight: FONT_WEIGHTS.semibold,
    },
    description: {
      fontSize: FONT_SIZES.md,
      color: colors.textMuted,
    },
  });
  return styles;
};
