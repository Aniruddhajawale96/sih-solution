import { Tabs } from "expo-router";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from "react-native";
import FontAwesome from "@expo/vector-icons/FontAwesome";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { useTheme } from "@/hooks/useTheme";
import withAlpha from "@/lib/helpers/withAlpha";
import PressableOpacity from "@/components/shared/PressableOpacity";
import SIZES from "@/constants/sizes";
import { FONT_SIZES, FONT_WEIGHTS } from "@/constants/fonts";

type IconName = React.ComponentProps<typeof FontAwesome>["name"];

type RouteIconMap = {
  [key: string]: IconName;
};

const icons: RouteIconMap = {
  "(home)/index": "home",
  "(home)": "home",
  home: "home",
  "(profile)/index": "user",
  "(profile)": "user",
  profile: "user",
  "(schemes)/index": "rupee",
  "(schemes)": "rupee",
  schemes: "rupee",
};

function CustomTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const colors = useTheme();
  return (
    <View style={styles.tabBar}>
      {state.routes.map((route, index) => {
        const isFocused = state.index === index;

        const iconName = icons[route.name as keyof typeof icons] || "question";

        // Clean up the label to remove parentheses
        const label = route.name.replace(/[()]/g, "");

        return (
          <PressableOpacity
            key={route.key}
            onPress={() => navigation.navigate(route.name)}
            style={styles.tabItem}
          >
            <FontAwesome
              name={iconName}
              size={SIZES.icon.MD}
              color={isFocused ? colors.primaryDark : colors.disabled}
              // #007AFF
            />

            <Text
              style={[
                styles.label,
                {
                  color: isFocused
                    ? withAlpha(colors.primaryDark, 0.6)
                    : "#999",
                },
              ]}
            >
              {label}
            </Text>
          </PressableOpacity>
        );
      })}
    </View>
  );
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <CustomTabBar {...props} />}
    >
      <Tabs.Screen name="(home)" />
      <Tabs.Screen name="(schemes)" />
      <Tabs.Screen name="(profile)" />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    flexDirection: "row",
    height: Dimensions.get("window").height * 0.075,
    backgroundColor: "#fff",
    borderTopWidth: 1,
    borderTopColor: "#eee",
  },
  tabItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  label: {
    fontSize: FONT_SIZES.sm,
    marginTop: SIZES.spacing.SPACING_4,
    textTransform: "capitalize",
    fontWeight: FONT_WEIGHTS.semibold,
  },
  iconWrapper: {
    paddingHorizontal: SIZES.spacing.SPACING_16,
    paddingVertical: SIZES.spacing.SPACING_8,
    borderRadius: SIZES.radius.FULL,
  },
  iconWrapperActive: {
    backgroundColor: "transparent", // set dynamically
  },
});
