import { useThree } from "@react-three/fiber/native";
import { PanResponder } from "react-native";
import { useEffect, useRef } from "react";
import * as THREE from "three";

type Props = {
  target?: THREE.Vector3;
  rotateSpeed?: number;
  panSpeed?: number;
};

export default function MobileCameraControls({
  target = new THREE.Vector3(0, 0, 0),
  rotateSpeed = 0.005,
  panSpeed = 0.002,
}: Props) {
  const { camera, gl } = useThree();

  const spherical = useRef(new THREE.Spherical());
  const start = useRef({ x: 0, y: 0 });
  const touches = useRef(0);

  useEffect(() => {
    spherical.current.setFromVector3(camera.position.clone().sub(target));
  }, []);

  const panResponder = PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onPanResponderGrant: (_, gesture) => {
      start.current = { x: gesture.x0, y: gesture.y0 };
      touches.current = gesture.numberActiveTouches;
    },

    onPanResponderMove: (_, gesture) => {
      const dx = gesture.moveX - start.current.x;
      const dy = gesture.moveY - start.current.y;

      start.current = { x: gesture.moveX, y: gesture.moveY };

      // ONE FINGER → ROTATE
      if (touches.current === 1) {
        spherical.current.theta -= dx * rotateSpeed;
        spherical.current.phi -= dy * rotateSpeed;

        spherical.current.phi = Math.max(
          0.4,
          Math.min(Math.PI / 2.1, spherical.current.phi),
        );
      }

      // TWO FINGERS → PAN
      if (touches.current === 2) {
        const panOffset = new THREE.Vector3(-dx, dy, 0).multiplyScalar(
          panSpeed,
        );
        panOffset.applyQuaternion(camera.quaternion);

        camera.position.add(panOffset);
        target.add(panOffset);
      }

      camera.position.setFromSpherical(spherical.current).add(target);

      camera.lookAt(target);
    },
  });

  useEffect(() => {
    gl.domElement.addEventListener("touchstart", () => {});
    gl.domElement.addEventListener("touchmove", () => {});
    gl.domElement.addEventListener("touchend", () => {});

    return () => {
      gl.domElement.removeEventListener("touchstart", () => {});
      gl.domElement.removeEventListener("touchmove", () => {});
      gl.domElement.removeEventListener("touchend", () => {});
    };
  }, []);

  return <primitive object={panResponder.panHandlers} />;
}
