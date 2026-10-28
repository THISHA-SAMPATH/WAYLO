// API & Domain Types for WAYLO Web Application

export interface TrajectoryPoint {
  t: number
  x: number
  y: number
  phi: number
  v: number
  alpha: number
  risk: number
  clear_left: number
  clear_right: number
  front_range: number
  aeb: boolean
}

export interface SimulationSummary {
  status?: string
  passed?: boolean
  passed_door?: boolean
  collision: boolean
  min_clearance_m?: number
  min_door_clearance_m?: number
  peak_alpha: number
  duration_s: number
  scrape_count?: number
  reason?: string
}

export interface SimulationConditionResult {
  trajectory: TrajectoryPoint[]
  summary: SimulationSummary
}

export interface ClosedLoopResponse {
  params: {
    drift_deg: number
    door_width_m: number
    tremor_deg: number
    duration_s: number
    reaction_delay_s?: number
    visual_gain?: number
    fatigue_rate?: number
  }
  unassisted: SimulationConditionResult
  corrective: SimulationConditionResult
  waylo: SimulationConditionResult
}

export interface PerceptionScanResponse {
  chair: { x: number; y: number; heading: number }
  doorway: {
    left_post: [number, number]
    right_post: [number, number]
    center: [number, number]
    width: number
    normal: [number, number]
  } | null
  ranges: number[]
  door_y: number
}

export interface VoiceCommandResponse {
  speed_cap_mps: number
  clearance_margin_m: number
  door_mode: string
  intent_summary: string
  source: string
  model: string
}

export interface IncidentNarrationResponse {
  summary: string
  source: string
  model: string
}

export interface AuditCall {
  timestamp: string
  model: string
  call_type: string
  latency_s: number
  tokens_estimated: number
  source: string
  input_excerpt: string
  output_excerpt: string
}

export interface NebiusAuditResponse {
  status: string
  total_calls: number
  token_factory_verified: boolean
  calls: AuditCall[]
}

export interface LedgerMetricsResponse {
  independence_ratio: number
  near_misses_avoided?: number
  scrapes_recorded?: number
  collisions_recorded?: number
  estimated_repair_cost_avoided_usd?: number
  event_counts?: {
    assist_engaged?: number
    near_miss?: number
    scrape?: number
    collision?: number
    human_rescue?: number
  }
  privacy_audit?: {
    images_stored: number
    cloud_telemetry_in_loop: number
    local_control_hz: number
    cloud_audit_isolated: boolean
  }
  cost_avoidance?: {
    estimated_dollars: number
    formula: string
    label: string
  }
}

export interface AccessibilityStandardResponse {
  region: string
  door_width_min_m?: number
  min_doorway_width_m?: number
  clearance_recommended_m?: number
  source: string
  title?: string
  url?: string
  content?: string
  standard_code?: string
  standards_context?: string
  standard_specs?: {
    doorway?: {
      min_width_meters?: number
      standard_code?: string
      guideline?: string
    }
  }
}

export interface ConditionStats {
  collision_rate: number
  collision_ci_95: [number, number]
  pass_rate: number
  pass_ci_95: [number, number]
  total_runs?: number
  collision_count?: number
  pass_count?: number
  min_door_clearance_passed_only?: {
    mean: number
    std: number
    median?: number
    ci_lower?: number
    ci_upper?: number
    count?: number
  }
  min_clearance_passed_mean?: number
  min_clearance_passed_std?: number
  n?: number
}

export interface MonteCarloSummaryResponse {
  metadata: {
    n_trials: number
    conditions: string[]
    door_widths: number[]
    master_seed?: number
    seed?: number
  }
  overall: {
    uncorrected?: ConditionStats
    unassisted?: ConditionStats
    corrective: ConditionStats
    waylo: ConditionStats
  }
  by_door_width: Record<string, {
    door_width_m?: number
    uncorrected?: ConditionStats
    unassisted?: ConditionStats
    corrective: ConditionStats
    waylo: ConditionStats
  }>
}

export interface SensitivityRow {
  sweep_param: string
  sweep_value: string
  condition: string
  collision_rate: string
  pass_rate: string
  min_clearance_mean: string
  notes: string
}

export interface SensitivitySweepResponse {
  status: string
  rows: SensitivityRow[]
}

export interface DepthBenchmarkFrame {
  frame_index: number
  file_name: string
  detected: boolean
  door_width_est_m: number | null
  ground_truth_width_m: number
  error_m: number | null
  confidence: number
  notes: string
}

export interface DepthBenchmarkResponse {
  total_frames: number
  detected_count: number
  failed_frames: number[]
  mean_door_width_error_m: number
  max_door_width_error_m: number
  frames: DepthBenchmarkFrame[]
}
