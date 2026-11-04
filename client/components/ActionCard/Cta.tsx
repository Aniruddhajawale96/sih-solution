import React, { useEffect } from "react";
import PressableOpacity from "../shared/PressableOpacity";
import FontAwesome6 from "@expo/vector-icons/FontAwesome6";
import { type PressableProps, StyleSheet } from "react-native";
import SIZES from "@/constants/sizes";
import { useTheme } from "@/hooks/useTheme";

import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withDelay,
} from "react-native-reanimated";

interface CtaProps extends PressableProps {
  style?: any;
}

const Cta = ({ onPress, style }: CtaProps) => {
  const styles = useStyles();

  const scale = useSharedValue(0.6);
  const rotate = useSharedValue(30); // slightly less than resting

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }, { rotateZ: `${rotate.value}deg` }],
  }));

  // 🔥 Load animation
  useEffect(() => {
    scale.value = withDelay(
      120,
      withSpring(1, {
        damping: 10,
        stiffness: 180,
      }),
    );
  }, []);

  return (
    <PressableOpacity
      onPress={onPress}
      style={[styles.button, style]}
      opacityAnimationConfig={{ dimOpacity: 0.7 }}
      onPressIn={() => {
        scale.value = withSpring(1.25, {
          damping: 8,
          stiffness: 180,
        });
        rotate.value = withSpring(52, {
          damping: 10,
          stiffness: 160,
        });
      }}
      onPressOut={() => {
        scale.value = withSpring(1, {
          damping: 10,
          stiffness: 200,
        });
        rotate.value = withSpring(45, {
          damping: 12,
          stiffness: 220,
        });
      }}
    >
      <Animated.View style={animatedStyle}>
        <FontAwesome6 name="arrow-up-long" size={SIZES.icon.XL} color="#fff" />
      </Animated.View>
    </PressableOpacity>
  );
};

const useStyles = () => {
  const colors = useTheme();

  return StyleSheet.create({
    button: {
      height: SIZES.image_sizes.AVATAR_XL,
      width: SIZES.image_sizes.AVATAR_XL,
      borderRadius: SIZES.radius.LG,
      backgroundColor: colors.primaryMuted,
      alignItems: "center",
      justifyContent: "center",

      // iOS shadow
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.25,
      shadowRadius: 8,

      // Android
      elevation: 6,
    },
  });
};

export default Cta;
