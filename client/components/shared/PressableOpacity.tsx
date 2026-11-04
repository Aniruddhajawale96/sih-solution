import React, { forwardRef } from "react";
import {
  Pressable,
  type PressableProps,
  type GestureResponderEvent,
  Platform,
} from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

export interface IPressableOpacityProps extends PressableProps {
  /**
   * configuration for opacity animation
   * @param fadeInDuration: fade in timing
   * @param fadeOutDuration: fade out timing
   * @param dimOpacity: lowest opacity when component is pressed
   */
  opacityAnimationConfig?: {
    fadeInDuration?: number;
    fadeOutDuration?: number;
    dimOpacity?: number;
  };

  /**
   * this option disables opacity animation when pressed on android
   */
  disableOpacityOnAndroid?: boolean;
}

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

const FADE_IN_DURATION = 50;
const FADE_OUT_DURATION = 100;
const DIM_OPACITY = 0.3;

const PressableOpacity = forwardRef<
  React.ComponentRef<typeof Pressable>,
  IPressableOpacityProps
>(
  (
    {
      children,
      style,
      onPressIn,
      onPressOut,
      disableOpacityOnAndroid,
      opacityAnimationConfig,
      ...restProps
    },
    ref
  ) => {
    const opacity = useSharedValue(1);

    const rStyle = useAnimatedStyle(() => ({
      opacity: opacity.value,
    }));

    const {
      fadeInDuration = FADE_IN_DURATION,
      fadeOutDuration = FADE_OUT_DURATION,
      dimOpacity = DIM_OPACITY,
    } = opacityAnimationConfig ?? {};

    const handlePressIn = (e: GestureResponderEvent) => {
      opacity.value = withTiming(dimOpacity, { duration: fadeInDuration });
      onPressIn?.(e);
    };

    const handlePressOut = (e: GestureResponderEvent) => {
      opacity.value = withTiming(1, { duration: fadeOutDuration });
      onPressOut?.(e);
    };

    const shouldBlockOpacityAnimationOnAndroid =
      Platform.OS === "android" && disableOpacityOnAndroid;

    return (
      <AnimatedPressable
        ref={ref}
        style={[style, rStyle]}
        onPressIn={!shouldBlockOpacityAnimationOnAndroid ? handlePressIn : null}
        onPressOut={
          !shouldBlockOpacityAnimationOnAndroid ? handlePressOut : null
        }
        {...restProps}
      >
        {children}
      </AnimatedPressable>
    );
  }
);

PressableOpacity.displayName = "PressableOpacity";
export default PressableOpacity;
