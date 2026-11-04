import { useColorScheme } from "react-native";
import { Colors, ThemeColors } from "@/constants/theme";

export function useTheme(): ThemeColors {
  const colorScheme = useColorScheme();
  const scheme: "light" | "dark" = colorScheme === "dark" ? "dark" : "light";

  return Colors[scheme];
}
