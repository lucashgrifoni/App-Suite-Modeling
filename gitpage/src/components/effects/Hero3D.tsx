import { Canvas, useFrame } from "@react-three/fiber";
import {
  Environment,
  Float,
  MeshDistortMaterial,
  PerspectiveCamera,
} from "@react-three/drei";
import { useRef, Suspense } from "react";
import type { Mesh } from "three";
import { tokens } from "../../lib/tokens";

function Core() {
  const mesh = useRef<Mesh>(null);
  useFrame((state) => {
    if (!mesh.current) return;
    mesh.current.rotation.x =
      state.clock.elapsedTime * 0.12 + Math.sin(state.clock.elapsedTime * 0.2) * 0.08;
    mesh.current.rotation.y = state.clock.elapsedTime * 0.22;
  });

  return (
    <Float speed={2} rotationIntensity={0.35} floatIntensity={0.6}>
      <mesh ref={mesh} scale={1.35}>
        <icosahedronGeometry args={[1, 2]} />
        <MeshDistortMaterial
          color={tokens.mint}
          roughness={0.2}
          metalness={0.85}
          distort={0.35}
          speed={2}
        />
      </mesh>
    </Float>
  );
}

function Ring() {
  const mesh = useRef<Mesh>(null);
  useFrame((state) => {
    if (!mesh.current) return;
    mesh.current.rotation.z = -state.clock.elapsedTime * 0.15;
  });
  return (
    <mesh ref={mesh} rotation={[Math.PI / 2.2, 0, 0]}>
      <torusGeometry args={[1.85, 0.02, 16, 100]} />
      <meshStandardMaterial
        color={tokens.steel}
        emissive={tokens.mint}
        emissiveIntensity={0.25}
        metalness={0.9}
        roughness={0.25}
      />
    </mesh>
  );
}

function Scene() {
  return (
    <>
      <PerspectiveCamera makeDefault position={[0, 0, 5.2]} fov={42} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[4, 6, 4]} intensity={1.1} color="#d5d8dd" />
      <pointLight position={[-3, -2, 2]} intensity={1.4} color={tokens.mint} />
      <Core />
      <Ring />
      <Environment preset="city" />
    </>
  );
}

export function Hero3D() {
  return (
    <div className="relative h-[min(52vh,420px)] w-full md:h-[min(56vh,480px)]">
      <Canvas
        className="!absolute inset-0"
        dpr={[1, 2]}
        gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}
      >
        <Suspense fallback={null}>
          <Scene />
        </Suspense>
      </Canvas>
    </div>
  );
}
