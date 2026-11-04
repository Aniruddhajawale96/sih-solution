import { StyleSheet, View, ViewProps } from "react-native";
import { PropsWithChildren } from "react";
import { useTheme } from "@/hooks/useTheme";
import SIZES from "@/constants/sizes";

export interface GroupCardProps extends PropsWithChildren, ViewProps {}

export default function GroupCard({
  children,
  style,
  ...props
}: GroupCardProps) {
  const styles = useStyles();
  return (
    <View {...props} style={[styles.cardStyle, style]}>
      {children}
    </View>
  );
}

const useStyles = () => {
  const colors = useTheme();
  const styles = StyleSheet.create({
    cardStyle: {
      backgroundColor: colors.cardBackground,
      width: "100%",
      paddingVertical: SIZES.spacing.SPACING_12,
      paddingHorizontal: SIZES.spacing.SPACING_20,
      borderRadius: SIZES.radius.LG,

      // iOS shadow
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.08,
      shadowRadius: 20,

      // Android shadow
      // elevation: 6,
    },
  });

  return styles;
};
