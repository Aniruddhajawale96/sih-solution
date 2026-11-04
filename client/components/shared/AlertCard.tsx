import { StyleSheet, Text, View, Dimensions } from "react-native";
import React from "react";
import { Ionicons } from "@expo/vector-icons";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  runOnJS,
  Layout,
} from "react-native-reanimated";
import { Gesture, GestureDetector } from "react-native-gesture-handler";

type AlertSeverity = "info" | "warning" | "critical";

interface AlertCardProps {
  title: string;
  message: string;
  severity?: AlertSeverity;
  onDismiss?: () => void;
}

const SCREEN_WIDTH = Dimensions.get("window").width;
const DISMISS_THRESHOLD = -SCREEN_WIDTH * 0.3;

const SEVERITY_CONFIG = {
  info: {
    color: "#2563eb",
    bg: "#eff6ff",
    label: "Info",
    icon: "notifications-outline",
  },
  warning: {
    color: "#d97706",
    bg: "#fff7ed",
    label: "Warning",
    icon: "alert-circle-outline",
  },
  critical: {
    color: "#dc2626",
    bg: "#fef2f2",
    label: "Critical",
    icon: "alert-outline",
  },
} as const;

const AlertCard: React.FC<AlertCardProps> = ({
  title,
  message,
  severity = "info",
  onDismiss,
}) => {
  const config = SEVERITY_CONFIG[severity];

  const translateX = useSharedValue(0);
  const opacity = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    opacity: opacity.value,
  }));

  const gesture = Gesture.Pan()
    .activeOffsetX([-20, 20]) // activate only on horizontal drag
    .failOffsetY([-10, 10])
    .onUpdate((e) => {
      translateX.value = Math.min(0, e.translationX);
    })
    .onEnd(() => {
      if (translateX.value < DISMISS_THRESHOLD) {
        translateX.value = withTiming(-SCREEN_WIDTH);
        opacity.value = withTiming(0, {}, () => {
          if (onDismiss) {
            runOnJS(onDismiss)();
          }
        });
      } else {
        translateX.value = withTiming(0);
      }
    });

  const onGestureEvent = (event: any) => {
    translateX.value = Math.min(0, event.translationX);
  };

  const onGestureEnd = () => {
    if (translateX.value < DISMISS_THRESHOLD) {
      translateX.value = withTiming(-SCREEN_WIDTH);
      opacity.value = withTiming(0, {}, () => {
        if (onDismiss) {
          runOnJS(onDismiss)();
        }
      });
    } else {
      translateX.value = withTiming(0);
    }
  };

  return (
    <Animated.View layout={Layout.springify()} style={styles.wrapper}>
      <GestureDetector gesture={gesture}>
        <Animated.View
          style={[
            styles.container,
            { backgroundColor: config.bg },
            animatedStyle,
          ]}
        >
          <View style={styles.header}>
            <View
              style={[
                styles.iconWrapper,
                { backgroundColor: config.color + "20" },
              ]}
            >
              <Ionicons name={config.icon} size={18} color={config.color} />
            </View>

            <View style={styles.titleRow}>
              <Text style={styles.title}>{title}</Text>

              <View
                style={[styles.badge, { backgroundColor: config.color + "20" }]}
              >
                <Text style={[styles.badgeText, { color: config.color }]}>
                  {config.label}
                </Text>
              </View>
            </View>
          </View>

          <Text style={styles.message}>{message}</Text>
        </Animated.View>
      </GestureDetector>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  wrapper: {
    marginBottom: 12,
  },
  container: {
    borderRadius: 12,
    padding: 14,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  iconWrapper: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 10,
  },
  titleRow: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    fontSize: 15,
    fontWeight: "600",
    color: "#111827",
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: "600",
  },
  message: {
    fontSize: 13,
    color: "#374151",
    lineHeight: 18,
  },
});

export default AlertCard;
