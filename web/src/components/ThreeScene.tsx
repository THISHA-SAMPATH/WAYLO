import React, { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import type { TrajectoryPoint } from '../types'

interface ThreeSceneProps {
  viewMode: 'world' | 'ai'
  doorWidthM: number
  unassistedPath: TrajectoryPoint[]
  wayloPath: TrajectoryPoint[]
  currentStepIndex: number
  showUnassisted: boolean
  showWaylo: boolean
}

const RoomEnvironment: React.FC<{
  viewMode: 'world' | 'ai'
  doorWidthM: number
}> = ({ viewMode, doorWidthM }) => {
  const isAI = viewMode === 'ai'
  const halfDoor = doorWidthM / 2
  const doorY = 4.5
  const wallZ = -doorY

  return (
    <group>
      {/* Floor */}
      <mesh position={[0, -0.01, -4.5]} receiveShadow>
        <planeGeometry args={[14, 16]} />
        <meshStandardMaterial
          color={isAI ? '#0B120E' : '#EAE6DD'}
          roughness={isAI ? 1.0 : 0.8}
          wireframe={isAI}
        />
      </mesh>

      {/* Grid lines */}
      <gridHelper
        args={[16, 32, isAI ? '#1F7A4D' : '#8A9991', isAI ? '#1A3326' : '#D0CBC0']}
        position={[0, 0.005, -4.5]}
      />

      {/* Left Wall Segment */}
      <mesh position={[(-7 - halfDoor) / 2, 0.6, wallZ]} castShadow receiveShadow>
        <boxGeometry args={[7 - halfDoor, 1.2, 0.15]} />
        <meshStandardMaterial
          color={isAI ? '#17352B' : '#FFFFFF'}
          wireframe={isAI}
          roughness={0.6}
        />
      </mesh>

      {/* Right Wall Segment */}
      <mesh position={[(7 + halfDoor) / 2, 0.6, wallZ]} castShadow receiveShadow>
        <boxGeometry args={[7 - halfDoor, 1.2, 0.15]} />
        <meshStandardMaterial
          color={isAI ? '#17352B' : '#FFFFFF'}
          wireframe={isAI}
          roughness={0.6}
        />
      </mesh>

      {/* Door Post Markers (Left & Right) */}
      <mesh position={[-halfDoor, 0.6, wallZ]}>
        <cylinderGeometry args={[0.08, 0.08, 1.25, 16]} />
        <meshStandardMaterial
          color={isAI ? '#E3F26D' : '#17352B'}
          emissive={isAI ? '#E3F26D' : '#000000'}
          emissiveIntensity={isAI ? 0.4 : 0}
        />
      </mesh>
      <mesh position={[halfDoor, 0.6, wallZ]}>
        <cylinderGeometry args={[0.08, 0.08, 1.25, 16]} />
        <meshStandardMaterial
          color={isAI ? '#E3F26D' : '#17352B'}
          emissive={isAI ? '#E3F26D' : '#000000'}
          emissiveIntensity={isAI ? 0.4 : 0}
        />
      </mesh>

      {/* Back Boundary Wall */}
      <mesh position={[0, 0.6, -8.0]}>
        <boxGeometry args={[14, 1.2, 0.15]} />
        <meshStandardMaterial
          color={isAI ? '#17352B' : '#D5D0C5'}
          wireframe={isAI}
        />
      </mesh>
    </group>
  )
}

// 3D Path Trail Line
const PathTrail: React.FC<{
  points: TrajectoryPoint[]
  color: string
  dashed?: boolean
}> = ({ points, color, dashed = false }) => {
  const lineObject = useMemo(() => {
    if (!points || points.length < 2) return null
    const pts = points.map((p) => new THREE.Vector3(p.x, 0.06, -p.y))
    const geom = new THREE.BufferGeometry().setFromPoints(pts)
    const mat = dashed
      ? new THREE.LineDashedMaterial({
          color,
          dashSize: 0.2,
          gapSize: 0.15,
          linewidth: 3,
        })
      : new THREE.LineBasicMaterial({ color, linewidth: 3 })
    const line = new THREE.Line(geom, mat)
    if (dashed) line.computeLineDistances()
    return line
  }, [points, color, dashed])

  if (!lineObject) return null

  return <primitive object={lineObject} />
}

// LiDAR Fan Projection
const LidarRays: React.FC<{
  chairPos: [number, number, number]
  headingDeg: number
  viewMode: 'world' | 'ai'
  doorWidthM: number
}> = ({ chairPos, headingDeg, viewMode, doorWidthM }) => {
  const segmentsObject = useMemo(() => {
    const pts: THREE.Vector3[] = []
    const baseHeadingRad = (headingDeg * Math.PI) / 180
    const halfDoor = doorWidthM / 2

    // 61 rays over 120 degree FOV
    for (let i = 0; i <= 60; i += 2) {
      const angleOffset = (-60 + i * 2) * (Math.PI / 180)
      const rayAngle = baseHeadingRad + angleOffset
      const dx = Math.cos(rayAngle)
      const dy = Math.sin(rayAngle)

      let dist = 4.0
      const currentY = -chairPos[2]
      const currentX = chairPos[0]

      if (dy > 0.05) {
        const tToDoor = (4.5 - currentY) / dy
        if (tToDoor > 0 && tToDoor < dist) {
          const hitX = currentX + tToDoor * dx
          if (Math.abs(hitX) >= halfDoor) {
            dist = tToDoor
          } else {
            const tToBack = (8.0 - currentY) / dy
            dist = Math.min(dist, Math.max(0.5, tToBack))
          }
        }
      }

      const endX = currentX + dist * dx
      const endY = currentY + dist * dy
      pts.push(new THREE.Vector3(chairPos[0], 0.08, chairPos[2]))
      pts.push(new THREE.Vector3(endX, 0.08, -endY))
    }

    const geom = new THREE.BufferGeometry().setFromPoints(pts)
    const mat = new THREE.LineBasicMaterial({
      color: viewMode === 'ai' ? '#E3F26D' : '#1F7A4D',
      transparent: true,
      opacity: viewMode === 'ai' ? 0.75 : 0.35,
    })
    return new THREE.LineSegments(geom, mat)
  }, [chairPos, headingDeg, viewMode, doorWidthM])

  return <primitive object={segmentsObject} />
}

// Wheelchair 3D Footprint
const WheelchairModel: React.FC<{
  point: TrajectoryPoint
  isWaylo: boolean
  viewMode: 'world' | 'ai'
}> = ({ point, isWaylo, viewMode }) => {
  const rotY = (point.phi * Math.PI) / 180 - Math.PI / 2
  const isAI = viewMode === 'ai'

  return (
    <group position={[point.x, 0.1, -point.y]} rotation={[0, -rotY, 0]}>
      {/* Base Chassis (0.68m width x 0.85m length) */}
      <mesh position={[0, 0.15, 0]} castShadow>
        <boxGeometry args={[0.68, 0.25, 0.85]} />
        <meshStandardMaterial
          color={
            isAI
              ? isWaylo
                ? '#1F7A4D'
                : '#C2410C'
              : isWaylo
              ? '#17352B'
              : '#A33310'
          }
          wireframe={isAI}
          roughness={0.4}
        />
      </mesh>

      {/* Seat backrest */}
      <mesh position={[0, 0.45, 0.2]}>
        <boxGeometry args={[0.55, 0.45, 0.1]} />
        <meshStandardMaterial
          color={isAI ? '#E3F26D' : '#334D41'}
          wireframe={isAI}
        />
      </mesh>

      {/* Wheels */}
      <mesh position={[-0.36, 0.12, 0.1]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.18, 0.18, 0.08, 16]} />
        <meshStandardMaterial color="#14201B" />
      </mesh>
      <mesh position={[0.36, 0.12, 0.1]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.18, 0.18, 0.08, 16]} />
        <meshStandardMaterial color="#14201B" />
      </mesh>

      {/* Front Heading Pointer */}
      <mesh position={[0, 0.16, -0.45]} rotation={[-Math.PI / 2, 0, 0]}>
        <coneGeometry args={[0.08, 0.2, 12]} />
        <meshStandardMaterial
          color={isWaylo ? '#E3F26D' : '#F26B3A'}
          emissive={isWaylo ? '#E3F26D' : '#F26B3A'}
          emissiveIntensity={0.5}
        />
      </mesh>
    </group>
  )
}

export const ThreeScene: React.FC<ThreeSceneProps> = ({
  viewMode,
  doorWidthM,
  unassistedPath = [],
  wayloPath = [],
  currentStepIndex = 0,
  showUnassisted = true,
  showWaylo = true,
}) => {
  const currentWayloPoint =
    wayloPath && wayloPath.length > 0
      ? wayloPath[Math.min(currentStepIndex, wayloPath.length - 1)]
      : { t: 0, x: 0, y: 0, phi: 90, v: 0.8, alpha: 0, risk: 0, clear_left: 0.5, clear_right: 0.5, front_range: 4.5, aeb: false }

  const currentUnassistedPoint =
    unassistedPath && unassistedPath.length > 0
      ? unassistedPath[Math.min(currentStepIndex, unassistedPath.length - 1)]
      : currentWayloPoint

  return (
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [0, 8.5, 6.5], fov: 42 }}
        shadows
        className="w-full h-full rounded-2xl"
      >
        <color attach="background" args={[viewMode === 'ai' ? '#090F0C' : '#F8F6F1']} />

        <ambientLight intensity={viewMode === 'ai' ? 0.4 : 0.85} />
        <directionalLight
          position={[6, 12, 4]}
          intensity={viewMode === 'ai' ? 0.3 : 1.2}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />

        <RoomEnvironment viewMode={viewMode} doorWidthM={doorWidthM} />

        {showUnassisted && unassistedPath && unassistedPath.length > 0 && (
          <PathTrail points={unassistedPath} color="#C2410C" dashed={true} />
        )}
        {showWaylo && wayloPath && wayloPath.length > 0 && (
          <PathTrail points={wayloPath} color="#1F7A4D" dashed={false} />
        )}

        {showWaylo && (
          <WheelchairModel
            point={currentWayloPoint}
            isWaylo={true}
            viewMode={viewMode}
          />
        )}
        {showUnassisted && (
          <WheelchairModel
            point={currentUnassistedPoint}
            isWaylo={false}
            viewMode={viewMode}
          />
        )}

        <LidarRays
          chairPos={[currentWayloPoint.x, 0, -currentWayloPoint.y]}
          headingDeg={currentWayloPoint.phi}
          viewMode={viewMode}
          doorWidthM={doorWidthM}
        />

        <OrbitControls
          enableDamping
          dampingFactor={0.08}
          minDistance={3}
          maxDistance={18}
          maxPolarAngle={Math.PI / 2.1}
          target={[0, 0.4, -4.0]}
        />
      </Canvas>
    </div>
  )
}
