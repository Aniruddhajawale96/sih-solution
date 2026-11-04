import { Dimensions, PixelRatio, Platform, TextStyle } from "react-native";

const { width } = Dimensions.get("window");

export const scaleFont = (size: number) => {
  const guidelineBaseWidth = 375;

  const scale = width / guidelineBaseWidth;
  const newSize = size * scale;

  // This respects font scaling settings on Android
  const finalSize = newSize * PixelRatio.getFontScale();

  // Optional: clamp to prevent extreme sizes
  const clamped = Math.min(Math.max(finalSize, 10), 64);

  return Math.round(PixelRatio.roundToNearestPixel(clamped));
};

export const FONT_SIZES = {
  xs: scaleFont(10),
  sm: scaleFont(12),
  base: scaleFont(14),
  md: scaleFont(16),
  lg: scaleFont(18),
  xl: scaleFont(20),
  "2xl": scaleFont(24),
  "3xl": scaleFont(30),
  "4xl": scaleFont(36),
  "5xl": scaleFont(48),
  "6xl": scaleFont(56),
};

/**
 * Normalized font weights across platforms
 * iOS supports numeric weights
 * Android prefers named weights unless using a custom font
 */
export const FONT_WEIGHTS: Record<
  | "thin"
  | "extraLight"
  | "light"
  | "regular"
  | "medium"
  | "semibold"
  | "bold"
  | "extraBold"
  | "black",
  TextStyle["fontWeight"]
> = Platform.select({
  ios: {
    thin: "100",
    extraLight: "200",
    light: "300",
    regular: "400",
    medium: "500",
    semibold: "600",
    bold: "700",
    extraBold: "800",
    black: "900",
  },
  android: {
    thin: "100",
    extraLight: "200",
    light: "300",
    regular: "normal",
    medium: "500",
    semibold: "600",
    bold: "bold",
    extraBold: "800",
    black: "900",
  },
  default: {
    thin: "100",
    extraLight: "200",
    light: "300",
    regular: "400",
    medium: "500",
    semibold: "600",
    bold: "700",
    extraBold: "800",
    black: "900",
  },
})!;
