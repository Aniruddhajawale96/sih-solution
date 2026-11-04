import { StyleSheet, Text, TextStyle, View, ViewStyle } from "react-native";
import React from "react";
import { useTheme } from "@/hooks/useTheme";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";

interface SectionTitleProps {
  title: string;
  description?: string;
  containerStyle?: ViewStyle;
  titleStyle?: TextStyle;
  descriptionStyle?: TextStyle;
}

const ScreenTitle: React.FC<SectionTitleProps> = ({
  title,
  description,
  containerStyle,
  descriptionStyle,
  titleStyle,
}) => {
  const styles = useStyles();
  return (
    <View style={containerStyle}>
      <Text style={[styles.title, titleStyle]}>{title}</Text>
      {description && (
        <Text style={[styles.description, descriptionStyle]}>
          {description}
        </Text>
      )}
    </View>
  );
};

export default ScreenTitle;

const useStyles = () => {
  const colors = useTheme();

  const styles = StyleSheet.create({
    title: {
      fontSize: FONT_SIZES["4xl"],
      fontWeight: FONT_WEIGHTS.semibold,
    },
    description: {
      fontSize: FONT_SIZES.md,
      color: colors.textMuted,
    },
  });
  return styles;
};
