import React, { useState, useEffect, useRef } from 'react'
import { ThreeScene } from './ThreeScene'
import { api } from '../api/client'
import type { ClosedLoopResponse, TrajectoryPoint } from '../types'
import {
  Play,
  Pause,
  RotateCcw,
  Sliders,
  Eye,
  EyeOff,
} from 'lucide-react'

export const LiveDemo: React.FC = () => {
  const [viewMode, setViewMode] = useState<'world' | 'ai'>('world')
  const [doorWidthM, setDoorWidthM] = useState<number>(1.1)
  const [driftDeg, setDriftDeg] = useState<number>(14.0)
  const [tremorDeg, setTremorDeg] = useState<number>(2.0)
  const [reactionDelayS, setReactionDelayS] = useState<number>(0.35)
  const [fatigueRate, setFatigueRate] = useState<number>(0.05)

  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [simData, setSimData] = useState<ClosedLoopResponse | null>(null)

  // Playback state
  const [stepIndex, setStepIndex] = useState<number>(0)
  const [isPlaying, setIsPlaying] = useState<boolean>(true)
  const [showUnassisted, setShowUnassisted] = useState<boolean>(true)
  const [showWaylo, setShowWaylo] = useState<boolean>(true)

  const playTimerRef = useRef<number | null>(null)

  // Fetch simulation
  const runSimulation = async (overrides?: {
    door?: number
    drift?: number
    tremor?: number
    delay?: number
    fatigue?: number
  }) => {
    setLoading(true)
    setError(null)
    const door = overrides?.door ?? doorWidthM
    const drift = overrides?.drift ?? driftDeg
    const tremor = overrides?.tremor ?? tremorDeg
    const delay = overrides?.delay ?? reactionDelayS
    const fatigue = overrides?.fatigue ?? fatigueRate

    try {
      const data = await api.simulateClosedLoop({
        door_width_m: door,
        drift_deg: drift,
        tremor_deg: tremor,
        reaction_delay_s: delay,
        fatigue_rate: fatigue,
      })
      setSimData(data)
      setStepIndex(0)
      setIsPlaying(true)
    } catch (err: any) {
      setError(err?.message || 'Simulation request failed')
    } finally {
      setLoading(false)
    }
  }

  // Run initial simulation on mount
  useEffect(() => {
    runSimulation()
  }, [])

  // Playback timer
  useEffect(() => {
    if (!isPlaying || !simData) return

    const maxSteps = Math.max(
      simData.waylo?.trajectory?.length || 0,
      simData.unassisted?.trajectory?.length || 0
    )

    playTimerRef.current = window.setInterval(() => {
      setStepIndex((prev) => {
        if (prev >= maxSteps - 1) {
          setIsPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, 80)

    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current)
    }
  }, [isPlaying, simData])

  const applyPreset = (preset: {
    door: number
    drift: number
    tremor: number
    delay: number
    fatigue: number
  }) => {
    setDoorWidthM(preset.door)
    setDriftDeg(preset.drift)
    setTremorDeg(preset.tremor)
    setReactionDelayS(preset.delay)
    setFatigueRate(preset.fatigue)
    runSimulation(preset)
  }

  const currentWayloPoint: TrajectoryPoint | undefined =
    simData?.waylo?.trajectory && simData.waylo.trajectory.length > 0
      ? simData.waylo.trajectory[Math.min(stepIndex, simData.waylo.trajectory.length - 1)]
      : undefined

  return (
    <section id="demo" className="py-16 md:py-28 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#17352B]/5 text-xs font-semibold text-[#17352B] mb-2">
            <span className="w-2 h-2 rounded-full bg-[#E3F26D]"></span>
            <span>Interactive 3D Digital Twin</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#14201B]">
            See the Shared-Autonomy <span className="marker-highlight">Twin</span>
          </h2>
          <p className="text-base sm:text-lg text-[#5B6B63] mt-2 max-w-2xl">
            Compare unassisted driver trajectory against WAYLO continuous dynamic window blending. Orbit, zoom, and test challenging drift angles.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center bg-white p-1.5 rounded-2xl border border-[#14201B]/10 shadow-sm self-start md:self-end">
          <button
            onClick={() => setViewMode('world')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all min-h-[44px] flex items-center gap-2 ${
              viewMode === 'world'
                ? 'bg-[#17352B] text-white shadow-sm'
                : 'text-[#5B6B63] hover:text-[#14201B]'
            }`}
          >
            <Eye className="w-4 h-4 text-[#E3F26D]" />
            <span>World view</span>
          </button>
          <button
            onClick={() => setViewMode('ai')}
            className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all min-h-[44px] flex items-center gap-2 ${
              viewMode === 'ai'
                ? 'bg-[#17352B] text-white shadow-sm'
                : 'text-[#5B6B63] hover:text-[#14201B]'
            }`}
          >
            <EyeOff className="w-4 h-4 text-[#E3F26D]" />
            <span>What the AI sees</span>
          </button>
        </div>
      </div>

      {/* Main Focal Card */}
      <div className="rounded-3xl bg-white border border-[#14201B]/10 shadow-soft-lg overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        {/* Left: 3D Canvas Scene (7 cols) */}
        <div className="lg:col-span-7 h-[420px] sm:h-[500px] lg:h-[620px] relative bg-[#0B120E] overflow-hidden">
          <ThreeScene
            viewMode={viewMode}
            doorWidthM={doorWidthM}
            unassistedPath={simData?.unassisted?.trajectory || []}
            wayloPath={simData?.waylo?.trajectory || []}
            currentStepIndex={stepIndex}
            showUnassisted={showUnassisted}
            showWaylo={showWaylo}
          />

          {/* Floating Canvas Overlays */}
          <div className="absolute top-4 left-4 z-10 flex flex-wrap gap-2 pointer-events-auto">
            <button
              onClick={() => setShowWaylo(!showWaylo)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 backdrop-blur-md border transition ${
                showWaylo
                  ? 'bg-[#1F7A4D]/90 text-white border-[#1F7A4D]'
                  : 'bg-white/70 text-[#5B6B63] border-white/40'
              }`}
            >
              <span className="w-3 h-1 bg-[#1F7A4D] rounded-full inline-block"></span>
              <span>WAYLO Path (solid)</span>
            </button>
            <button
              onClick={() => setShowUnassisted(!showUnassisted)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 backdrop-blur-md border transition ${
                showUnassisted
                  ? 'bg-[#C2410C]/90 text-white border-[#C2410C]'
                  : 'bg-white/70 text-[#5B6B63] border-white/40'
              }`}
            >
              <span className="w-3 h-1 border-t-2 border-dashed border-[#C2410C] inline-block"></span>
              <span>Driver (red dashed)</span>
            </button>
          </div>

          <div className="absolute top-4 right-4 z-10 text-right pointer-events-none">
            <span className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-black/60 text-[#E3F26D] backdrop-blur-sm border border-white/10">
              Orbit/Zoom Enabled
            </span>
          </div>

          {/* Scrubber & Playback Controls Bar */}
          <div className="absolute bottom-4 left-4 right-4 z-10 bg-black/70 backdrop-blur-md p-3 rounded-2xl border border-white/10 text-white flex items-center gap-3">
            <button
              onClick={() => {
                const maxSteps = Math.max(
                  simData?.waylo?.trajectory?.length || 0,
                  simData?.unassisted?.trajectory?.length || 0
                )
                if (stepIndex >= maxSteps - 1) {
                  setStepIndex(0)
                  setIsPlaying(true)
                } else {
                  setIsPlaying(!isPlaying)
                }
              }}
              aria-label={isPlaying ? 'Pause simulation replay' : 'Play simulation replay'}
              className="w-10 h-10 rounded-xl bg-[#E3F26D] text-[#17352B] flex items-center justify-center font-bold hover:bg-white transition shrink-0 min-h-[40px]"
            >
              {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
            </button>

            <button
              onClick={() => {
                setStepIndex(0)
                setIsPlaying(true)
              }}
              aria-label="Restart simulation replay"
              className="p-2 rounded-lg hover:bg-white/10 text-white/80 transition shrink-0 min-h-[40px]"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Slider Scrubber */}
            <input
              type="range"
              min={0}
              max={
                simData
                  ? Math.max(
                      (simData.waylo?.trajectory?.length || 1) - 1,
                      (simData.unassisted?.trajectory?.length || 1) - 1
                    )
                  : 50
              }
              value={stepIndex}
              onChange={(e) => {
                setStepIndex(Number(e.target.value))
                setIsPlaying(false)
              }}
              className="w-full accent-[#E3F26D] h-2 bg-white/20 rounded-lg cursor-pointer"
            />

            <span className="text-xs font-mono text-white/80 shrink-0">
              {currentWayloPoint ? `${currentWayloPoint.t.toFixed(1)}s` : '0.0s'}
            </span>
          </div>
        </div>

        {/* Right: Controls & Presets (5 cols) */}
        <div className="lg:col-span-5 p-6 sm:p-8 flex flex-col justify-between space-y-6">
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-[#14201B]/10">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-[#17352B]" />
                <h3 className="font-bold text-lg text-[#14201B]">Simulation Controls</h3>
              </div>
              <span className="text-xs text-[#5B6B63] font-mono">DWA 50Hz</span>
            </div>

            {/* Presets */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-[#5B6B63] uppercase tracking-wider block">
                User Profile Presets
              </label>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <button
                  type="button"
                  onClick={() =>
                    applyPreset({ door: 1.1, drift: 8, tremor: 1.5, delay: 0.25, fatigue: 0.02 })
                  }
                  className="p-2.5 rounded-xl border border-[#14201B]/10 hover:border-[#17352B] bg-[#F4F2EC]/60 text-left transition font-medium"
                >
                  <p className="font-semibold text-[#14201B]">Mild Tremor</p>
                  <p className="text-[10px] text-[#5B6B63]">1.1m door, 8° drift</p>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    applyPreset({ door: 0.81, drift: 12, tremor: 2.0, delay: 0.35, fatigue: 0.05 })
                  }
                  className="p-2.5 rounded-xl border border-[#14201B]/10 hover:border-[#17352B] bg-[#F4F2EC]/60 text-left transition font-medium"
                >
                  <p className="font-semibold text-[#14201B]">ADA 0.81m Door</p>
                  <p className="text-[10px] text-[#5B6B63]">Narrow 32-inch gate</p>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    applyPreset({ door: 1.2, drift: 20, tremor: 3.5, delay: 0.45, fatigue: 0.08 })
                  }
                  className="p-2.5 rounded-xl border border-[#14201B]/10 hover:border-[#17352B] bg-[#F4F2EC]/60 text-left transition font-medium"
                >
                  <p className="font-semibold text-[#14201B]">Severe Drift (20°)</p>
                  <p className="text-[10px] text-[#5B6B63]">Off-axis approach</p>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    applyPreset({ door: 0.95, drift: 15, tremor: 4.0, delay: 0.65, fatigue: 0.12 })
                  }
                  className="p-2.5 rounded-xl border border-[#14201B]/10 hover:border-[#17352B] bg-[#F4F2EC]/60 text-left transition font-medium"
                >
                  <p className="font-semibold text-[#14201B]">Delayed Reaction</p>
                  <p className="text-[10px] text-[#5B6B63]">0.65s delay, fatigue</p>
                </button>
              </div>
            </div>

            {/* Sliders */}
            <div className="space-y-4 text-xs sm:text-sm">
              {/* Door Width */}
              <div>
                <div className="flex justify-between font-semibold mb-1 text-[#14201B]">
                  <span>Door Width:</span>
                  <span className="font-mono text-[#17352B] font-bold">{doorWidthM.toFixed(2)} m</span>
                </div>
                <input
                  type="range"
                  min="0.80"
                  max="2.00"
                  step="0.05"
                  value={doorWidthM}
                  onChange={(e) => setDoorWidthM(parseFloat(e.target.value))}
                  className="w-full accent-[#17352B]"
                />
                <div className="flex justify-between text-[10px] text-[#5B6B63]">
                  <span>0.80m (ADA min)</span>
                  <span>1.40m (Standard double)</span>
                  <span>2.00m</span>
                </div>
              </div>

              {/* Heading Drift */}
              <div>
                <div className="flex justify-between font-semibold mb-1 text-[#14201B]">
                  <span>Driver Heading Drift:</span>
                  <span className="font-mono text-[#F26B3A] font-bold">
                    {driftDeg > 0 ? `+${driftDeg.toFixed(0)}°` : `${driftDeg.toFixed(0)}°`}
                  </span>
                </div>
                <input
                  type="range"
                  min="-25"
                  max="25"
                  step="1"
                  value={driftDeg}
                  onChange={(e) => setDriftDeg(parseFloat(e.target.value))}
                  className="w-full accent-[#F26B3A]"
                />
                <div className="flex justify-between text-[10px] text-[#5B6B63]">
                  <span>-25° (Left)</span>
                  <span>0° (Centered)</span>
                  <span>+25° (Right)</span>
                </div>
              </div>

              {/* Hand Tremor */}
              <div>
                <div className="flex justify-between font-semibold mb-1 text-[#14201B]">
                  <span>Joystick Tremor Noise:</span>
                  <span className="font-mono text-[#14201B]">{tremorDeg.toFixed(1)}°</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="8"
                  step="0.5"
                  value={tremorDeg}
                  onChange={(e) => setTremorDeg(parseFloat(e.target.value))}
                  className="w-full accent-[#17352B]"
                />
              </div>

              {/* Reaction Delay */}
              <div>
                <div className="flex justify-between font-semibold mb-1 text-[#14201B]">
                  <span>Reaction Delay:</span>
                  <span className="font-mono text-[#14201B]">{reactionDelayS.toFixed(2)} s</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="1.00"
                  step="0.05"
                  value={reactionDelayS}
                  onChange={(e) => setReactionDelayS(parseFloat(e.target.value))}
                  className="w-full accent-[#17352B]"
                />
              </div>
            </div>
          </div>

          {/* Action CTA */}
          <div className="pt-4 border-t border-[#14201B]/10 space-y-3">
            <button
              onClick={() => runSimulation()}
              disabled={loading}
              id="btn-run-simulation"
              className="w-full py-4 rounded-2xl bg-[#17352B] hover:bg-[#1f473a] text-white font-semibold text-base transition shadow-md hover:shadow-lg disabled:opacity-50 min-h-[52px] flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                  <span>Computing 50Hz trajectory...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current text-[#E3F26D]" />
                  <span>Run Simulation</span>
                </>
              )}
            </button>

            {error && (
              <p className="text-xs text-red-600 bg-red-50 p-2.5 rounded-xl border border-red-200">
                {error}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Trajectory Outcome & Telemetry Strip */}
      {simData && (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Driver Unassisted Outcome */}
          <div
            className={`p-5 rounded-2xl border transition-all ${
              simData.unassisted.summary.collision
                ? 'bg-red-50/70 border-red-200 text-red-950'
                : 'bg-white border-[#14201B]/10'
            }`}
          >
            <div className="flex items-center justify-between text-xs font-semibold mb-2">
              <span className="text-[#C2410C]">Driver Unassisted</span>
              {simData.unassisted.summary.collision ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#C2410C] text-white">
                  COLLISION
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#1F7A4D] text-white">
                  PASSED
                </span>
              )}
            </div>
            <p className="text-2xl font-bold font-mono">
              {((simData.unassisted.summary.min_clearance_m ?? 0) * 100).toFixed(1)} cm
            </p>
            <p className="text-xs text-[#5B6B63] mt-1">
              Minimum post clearance ({simData.unassisted.summary.scrape_count || 0} scrapes)
            </p>
          </div>

          {/* WAYLO Blended Outcome */}
          <div className="p-5 rounded-2xl bg-[#17352B] text-white border border-[#17352B] shadow-sm">
            <div className="flex items-center justify-between text-xs font-semibold mb-2">
              <span className="text-[#E3F26D]">WAYLO Shared Autonomy</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E3F26D] text-[#17352B]">
                {simData.waylo.summary.passed ? 'SAFE PASS' : 'FALLBACK AEB'}
              </span>
            </div>
            <p className="text-2xl font-bold font-mono text-white">
              +{((simData.waylo.summary.min_clearance_m ?? 0) * 100).toFixed(1)} cm
            </p>
            <p className="text-xs text-white/70 mt-1">
              Peak blend α: {((simData.waylo.summary.peak_alpha ?? 0) * 100).toFixed(0)}% intervention
            </p>
          </div>

          {/* Telemetry Point Instant */}
          <div className="p-5 rounded-2xl bg-white border border-[#14201B]/10">
            <div className="text-xs font-semibold text-[#5B6B63] mb-2 uppercase">
              Current Scrubber Telemetry
            </div>
            <p className="text-2xl font-bold font-mono text-[#14201B]">
              α = {currentWayloPoint ? currentWayloPoint.alpha.toFixed(2) : '0.00'}
            </p>
            <div className="flex justify-between text-xs text-[#5B6B63] mt-1">
              <span>Risk: {currentWayloPoint ? currentWayloPoint.risk.toFixed(2) : '0.0'}</span>
              <span>Speed: {currentWayloPoint ? currentWayloPoint.v.toFixed(2) : '0.0'} m/s</span>
            </div>
          </div>

          {/* Clearance Margin Avoidance */}
          <div className="p-5 rounded-2xl bg-white border border-[#14201B]/10">
            <div className="text-xs font-semibold text-[#5B6B63] mb-2 uppercase">
              Left / Right Post Dist
            </div>
            <p className="text-2xl font-bold font-mono text-[#1F7A4D]">
              {currentWayloPoint
                ? `L: ${(currentWayloPoint.clear_left * 100).toFixed(0)}cm · R: ${(
                    currentWayloPoint.clear_right * 100
                  ).toFixed(0)}cm`
                : '—'}
            </p>
            <p className="text-xs text-[#5B6B63] mt-1">
              Active dynamic window centering
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
