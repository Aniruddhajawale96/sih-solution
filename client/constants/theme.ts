/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import { Platform } from "react-native";

// theme.ts
export interface ThemeColors {
  primary: string;
  primaryDark: string;
  primaryMuted: string;
  primaryElevated: string;
  background: string;
  backgroundMuted: string;
  cardBackground: string;
  cardBackgroundMuted: string;
  iconBackgroundPrimary: string;
  text: string;
  textLight: string;
  textMuted: string;
  textPrimaryBackground: string;
  anchor: string;
  overlayBackground: string;
  border: string;
  borderFocus: string;
  borderFocusMuted: string;
  placeholder: string;
  success: string;
  successMuted: string;
  successDark: string;
  error: string;
  errorMuted: string;
  glassTint: string;
  glassBorder: string;
  shadow: string;
  errorLight: string;
  warning: string;
  warningDark: string;
  blue: string;
  disabled: string;
}

const light: ThemeColors = {
  primary: "#99e2b4",
  primaryDark: "#41752a",
  primaryMuted: "#358f80",
  primaryElevated: "#e4fcd9",

  background: "#f1f1f1",
  backgroundMuted: "#FFF4EF",

  cardBackground: "#fff",
  cardBackgroundMuted: "#eee",

  iconBackgroundPrimary: "#e4fcd9",

  text: "#1F1F1F",
  textLight: "#fff",
  textMuted: "#979797",

  textPrimaryBackground: "#FFFFFF",
  anchor: "#3C366B",
  overlayBackground: "rgba(0, 0, 0, 0.4)",

  border: "#E6E6E6",
  borderFocus: "#89f759",
  borderFocusMuted: "#befaa5",

  placeholder: "#9E9E9E",

  success: "#2ECC71",
  successMuted: "#DFF5E7",
  successDark: "#1e864a",

  error: "#E74C3C",
  errorMuted: "#FADBD8",

  glassTint: "rgba(0, 0, 0, 0.06)",
  glassBorder: "rgba(255,255,255,0.35)",
  shadow: "#000",
  errorLight: "#F87171",

  warning: "#ffe45e",
  warningDark: "#9e8e3c",
  disabled: "#999",
  blue: "#5ebfe9",
};

const dark: ThemeColors = {
  primary: "#99e2b4",
  primaryDark: "#41752a",
  primaryMuted: "#68bd44",
  primaryElevated: "#e4fcd9",

  background: "#0F0F0F",
  backgroundMuted: "#1A1A1A",

  cardBackground: "#333",
  cardBackgroundMuted: "#555",

  iconBackgroundPrimary: "#7cc75b",

  text: "#FFFFFF",
  textLight: "#000",
  textMuted: "#B3B3B3",

  textPrimaryBackground: "#1A1A1A",
  anchor: "#3C366B",
  overlayBackground: "rgba(0, 0, 0, 0.6)",

  border: "#2A2A2A",
  borderFocus: "#89f759",
  borderFocusMuted: "#befaa5",

  placeholder: "#7A7A7A",

  success: "#2ECC71",
  successMuted: "#1E3A2A",
  successDark: "#1e864a",

  error: "#E74C3C",
  errorMuted: "#3A1E1E",

  glassTint: "rgba(0, 0, 0, 0.06)",
  glassBorder: "rgba(255,255,255,0.35)",
  shadow: "#000",
  errorLight: "#F87171",

  warning: "#ffe45e",
  warningDark: "#c3af49",

  disabled: "#999",

  blue: "#5ebfe9",
};

export const Colors = {
  light,
  dark,
};

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: "system-ui",
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: "ui-serif",
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: "ui-rounded",
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: "ui-monospace",
  },
  default: {
    sans: "normal",
    serif: "serif",
    rounded: "normal",
    mono: "monospace",
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded:
      "'SF Pro Rounded', 'Hiragino Maru Gothic ProN', Meiryo, 'MS PGothic', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
});
