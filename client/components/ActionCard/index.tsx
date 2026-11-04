import {
  Image,
  PressableProps,
  StyleSheet,
  View,
  ViewProps,
  ViewStyle,
} from "react-native";
import { PropsWithChildren } from "react";
import { useTheme } from "@/hooks/useTheme";
import SIZES from "@/constants/sizes";
import { LinearGradient } from "expo-linear-gradient";
import Cta from "./Cta";

export interface ActionProps extends PropsWithChildren, ViewProps {
  imageUri?: string;
  containerStyle?: ViewStyle;
  onCta: PressableProps["onPress"];
}

export default function Action({
  children,
  imageUri,
  style,
  containerStyle,
  onCta,
  ...props
}: ActionProps) {
  const styles = useStyles();
  return (
    <View style={[styles.cardContainerStyle, containerStyle]}>
      <View style={styles.imageStyle}>
        <Image
          source={imageUri ? { uri: imageUri } : undefined}
          height={300}
          style={[StyleSheet.absoluteFillObject, { opacity: 0.5 }]}
        />
        <LinearGradient
          colors={["transparent", "rgba(0,0,0,0.75)"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
          style={StyleSheet.absoluteFillObject}
        />
      </View>
      <View {...props} style={[styles.cardStyle, style]}>
        {children}
      </View>
      <Cta style={styles.ctaButton} onPress={onCta} />
    </View>
  );
}

const useStyles = () => {
  const colors = useTheme();
  const styles = StyleSheet.create({
    cardStyle: {
      paddingVertical: SIZES.spacing.SPACING_12,
      paddingHorizontal: SIZES.spacing.SPACING_20,
    },
    cardContainerStyle: {
      width: "100%",
      position: "relative",
      backgroundColor: colors.cardBackground,
      borderRadius: SIZES.radius.XL,

      // iOS shadow
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.08,
      shadowRadius: 20,

      // Android shadow
      elevation: 6,
      overflow: "hidden",
    },
    imageStyle: {
      position: "absolute",
      top: 0,
      left: 0,
      height: "100%",
      width: "100%",
      flex: 1,
    },
    ctaButton: {
      position: "absolute",
      bottom: SIZES.spacing.SPACING_12,
      right: SIZES.spacing.SPACING_12,
      zIndex: 2,
    },
  });

  return styles;
};
