import { View, Text, StyleSheet } from "react-native";
import * as THREE from "three";
import React, { useRef } from "react";

type Props = {
  cameraRef: React.RefObject<THREE.PerspectiveCamera | null>;
};

export const ZoomButtons = ({ cameraRef }: Props) => {
  const isZooming = useRef(false);

  const lerpZoom = (scale: number) => {
    if (!cameraRef.current || isZooming.current) return;

    isZooming.current = true;

    const camera = cameraRef.current;
    const start = camera.position.clone();
    const target = start.clone().multiplyScalar(scale);

    let t = 0;
    const duration = 12; // frames (lower = faster)

    const animate = () => {
      t++;
      const alpha = t / duration;

      camera.position.lerpVectors(start, target, alpha);

      if (t < duration) {
        requestAnimationFrame(animate);
      } else {
        camera.position.copy(target);
        isZooming.current = false;
      }
    };

    animate();
  };

  return (
    <View style={styles.container}>
      <Text style={styles.button} onPress={() => lerpZoom(0.85)}>
        ＋
      </Text>
      <Text style={styles.button} onPress={() => lerpZoom(1.15)}>
        －
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    right: 16,
    bottom: 40,
    gap: 10,
  },
  button: {
    backgroundColor: "rgba(0,0,0,0.7)",
    color: "#fff",
    fontSize: 22,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    textAlign: "center",
  },
});
