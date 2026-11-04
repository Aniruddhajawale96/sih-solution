import React, { useMemo, useRef } from "react";
import * as THREE from "three";
import { useGLTF } from "@react-three/drei/native";
import wheatModel from "@/assets/models/wheat.glb";
import riceModel from "@/assets/models/rice.glb";
import sugarcaneModel from "@/assets/models/sugarcane.glb";
import abcModel from "@/assets/models/abc.glb";
import cornModel from "@/assets/models/corn.glb";
import maizeModel from "@/assets/models/maize.glb";
import onionModel from "@/assets/models/onion.glb";
import tomatoModel from "@/assets/models/tomato.glb";
import { Text, View } from "react-native";
import { CROP_INFO } from "@/constants/defaults";

// Crop model configuration type
type CropConfig = {
  model: any;
  nodeName: string;
  materialName: string;
  scale: number;
  spacing: { x: number; z: number };
};

// Crop model configurations
const CROP_CONFIGS: Record<string, CropConfig> = {
  wheat: {
    model: wheatModel,
    nodeName: "Wheat_single_Plants_0",
    materialName: "Plants",
    scale: 18,
    spacing: { x: 20, z: 15 },
  },
  corn: {
    model: cornModel,
    nodeName: "Corn_single_Plants_0",
    materialName: "Plants.001",
    scale: 18,
    spacing: { x: 15, z: 15 },
  },
  maize: {
    model: maizeModel,
    nodeName: "Tomato_single_Plants_0",
    materialName: "Plants.002",
    scale: 16,
    spacing: { x: 14, z: 14 },
  },
  onion: {
    model: onionModel,
    nodeName: "Onion_single_Plants_0",
    materialName: "Plants.004",
    scale: 16,
    spacing: { x: 14, z: 14 },
  },
  rice: {
    model: riceModel,
    nodeName: "Rice_Plants_0",
    materialName: "Plants",
    scale: 15,
    spacing: { x: 12, z: 12 },
  },
  sugarcane: {
    model: sugarcaneModel,
    nodeName: "Sugarcane_Plants_0",
    materialName: "Plants",
    scale: 20,
    spacing: { x: 18, z: 18 },
  },
  tomato: {
    model: tomatoModel,
    nodeName: "Tomato_single_Plants_0",
    materialName: "Plants.002",
    scale: 16,
    spacing: { x: 14, z: 14 },
  },
};

const CropBase = ({
  geometry,
  material,
  id,
  crop = "wheat",
  isSelected,
  onSelect,
}: {
  geometry: THREE.ExtrudeGeometry;
  material: THREE.MeshStandardMaterial;
  id: string;
  crop: "wheat" | "rice" | "sugarcane" | "tomato" | "corn" | "none" | "maize";
  isSelected: boolean;
  onSelect: (id: string) => void;
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const isAnimatingRef = useRef(false);

  const initialPositionRef = useRef<THREE.Vector3 | null>(null);
  const initialScaleRef = useRef<THREE.Vector3 | null>(null);

  React.useEffect(() => {
    if (!groupRef.current) return;

    if (!initialPositionRef.current) {
      initialPositionRef.current = groupRef.current.position.clone();
    }

    if (!initialScaleRef.current) {
      initialScaleRef.current = groupRef.current.scale.clone();
    }
  }, []);

  React.useEffect(() => {
    if (!initialPositionRef.current || !initialScaleRef.current) return;

    if (isSelected) {
      animateIn();
    } else {
      animateOut();
    }
  }, [isSelected]);

  // Get the crop configuration
  const cropConfig = CROP_CONFIGS[crop];

  // Load the appropriate model
  const { nodes, materials } = useGLTF(
    cropConfig ? cropConfig.model : wheatModel,
  ) as any;

  // Get bounds of the geometry to create a grid
  const bounds = useMemo(() => {
    geometry.computeBoundingBox();
    const box = geometry.boundingBox!;
    return {
      minX: box.min.x,
      maxX: box.max.x,
      minY: box.min.y,
      maxY: box.max.y,
      minZ: box.min.z,
      maxZ: box.max.z,
      centerX: (box.min.x + box.max.x) / 2,
      centerY: (box.min.y + box.max.y) / 2,
      width: box.max.x - box.min.x,
      height: box.max.y - box.min.y,
    };
  }, [geometry]);

  // Create instanced mesh for better performance
  const { instancedMesh1, instancedMesh2, count } = useMemo(() => {
    // If crop is "none" or no config, return empty
    if (crop === "none" || !cropConfig) {
      return { instancedMesh1: null, instancedMesh2: null, count: 0 };
    }

    const spacing = cropConfig.spacing;

    // Calculate how many plants fit in this section dynamically
    const plantsPerRow = Math.ceil(bounds.width / spacing.x);
    const rows = Math.ceil(bounds.height / spacing.z);

    // Calculate starting position to align with bounds
    const startX = bounds.minX;
    const startY = bounds.minY;

    // Get the correct geometry node
    const plantGeometry = nodes[cropConfig.nodeName]?.geometry;
    if (!plantGeometry) {
      console.warn(`Geometry node "${cropConfig.nodeName}" not found in model`);
      return { instancedMesh1: null, instancedMesh2: null, count: 0 };
    }

    // Create a temporary mesh for raycasting
    const tempMesh = new THREE.Mesh(geometry, material);
    tempMesh.userData.id = id;

    // Create raycaster
    const raycaster = new THREE.Raycaster();
    const rayDirection = new THREE.Vector3(0, 0, -1); // Cast downward

    // Collect valid positions
    const validPositions: THREE.Vector3[] = [];

    for (let z = 0; z < rows; z++) {
      for (let x = 0; x < plantsPerRow; x++) {
        const posX = startX + x * spacing.x;
        const posY = startY + z * spacing.z;

        // Cast a ray from above the plant position downward
        const rayOrigin = new THREE.Vector3(posX, posY, bounds.maxZ + 10);
        raycaster.set(rayOrigin, rayDirection);

        // Check if ray intersects with this mesh
        const intersects = raycaster.intersectObject(tempMesh, false);

        // Only add plant if ray hits the TOP face (highest Z)
        if (intersects.length > 0) {
          // Get the intersection with the highest Z value (top surface)
          const topIntersect = intersects.reduce(
            (max, curr) => (curr.point.z > max.point.z ? curr : max),
            intersects[0],
          );

          validPositions.push(
            new THREE.Vector3(posX, posY, topIntersect.point.z - 10),
          );
        }
      }
    }

    // Clean up
    tempMesh.geometry.dispose();

    if (validPositions.length === 0) {
      return { instancedMesh1: null, instancedMesh2: null, count: 0 };
    }

    // Create instanced meshes for better performance
    const plantMaterial = materials[cropConfig.materialName].clone();
    plantMaterial.side = THREE.DoubleSide;

    const mesh1 = new THREE.InstancedMesh(
      plantGeometry,
      plantMaterial,
      validPositions.length,
    );

    const mesh2 = new THREE.InstancedMesh(
      plantGeometry,
      plantMaterial,
      validPositions.length,
    );

    // Set transforms for each instance
    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const quaternion = new THREE.Quaternion();
    const scale = new THREE.Vector3(
      cropConfig.scale,
      cropConfig.scale,
      cropConfig.scale,
    );

    // Since your original code used [0, Math.PI, 0] and Z is vertical (up),
    // we keep rotation around Z axis but ensure plants point up
    const rotation1 = new THREE.Euler(0, Math.PI, 0); // Flip 180° around Y
    const rotation2 = new THREE.Euler(0, Math.PI + Math.PI / 2, 0); // Flip + 90° for cross effect

    validPositions.forEach((pos, i) => {
      // First orientation
      position.copy(pos);
      quaternion.setFromEuler(rotation1);
      matrix.compose(position, quaternion, scale);
      mesh1.setMatrixAt(i, matrix);

      // Second orientation - perpendicular
      position.copy(pos);
      quaternion.setFromEuler(rotation2);
      matrix.compose(position, quaternion, scale);
      mesh2.setMatrixAt(i, matrix);
    });

    mesh1.instanceMatrix.needsUpdate = true;
    mesh2.instanceMatrix.needsUpdate = true;

    return {
      instancedMesh1: mesh1,
      instancedMesh2: mesh2,
      count: validPositions.length,
    };
  }, [nodes, materials, bounds, crop, cropConfig, geometry, material, id]);

  const animateIn = () => {
    if (!groupRef.current || isAnimatingRef.current) return;

    isAnimatingRef.current = true;

    const group = groupRef.current;
    const startPos = group.position.clone();
    const startScale = group.scale.clone();

    const targetPos = initialPositionRef
      .current!.clone()
      .add(new THREE.Vector3(0, 0, -30));
    const targetScale = initialScaleRef.current!.clone().multiplyScalar(1.5);

    animateTransform(group, startPos, targetPos, startScale, targetScale);
  };
  const animateOut = () => {
    if (!groupRef.current || isAnimatingRef.current) return;

    isAnimatingRef.current = true;

    const group = groupRef.current;

    animateTransform(
      group,
      group.position.clone(),
      initialPositionRef.current!,
      group.scale.clone(),
      initialScaleRef.current!,
    );
  };
  const animateTransform = (
    group: THREE.Group,
    startPos: THREE.Vector3,
    targetPos: THREE.Vector3,
    startScale: THREE.Vector3,
    targetScale: THREE.Vector3,
  ) => {
    let t = 0;
    const duration = 18;

    const animate = () => {
      t++;
      const alpha = t / duration;
      const eased = 1 - Math.pow(1 - alpha, 3);

      group.position.lerpVectors(startPos, targetPos, eased);
      group.scale.lerpVectors(startScale, targetScale, eased);

      if (t < duration) {
        requestAnimationFrame(animate);
      } else {
        group.position.copy(targetPos);
        group.scale.copy(targetScale);
        isAnimatingRef.current = false;
      }
    };

    animate();
  };

  return (
    <group ref={groupRef}>
      {/* Instanced crop field - MUCH better performance */}
      {instancedMesh1 && <primitive object={instancedMesh1} />}
      {instancedMesh2 && <primitive object={instancedMesh2} />}

      {/* Visible farm section */}
      <mesh
        ref={meshRef}
        geometry={geometry}
        material={material}
        userData={{ id }}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(id);
          console.log(id, "clicked");
        }}
      />
    </group>
  );
};

export default CropBase;
