import type {
  ClosedLoopResponse,
  SimulationConditionResult,
  SimulationSummary,
  TrajectoryPoint,
  PerceptionScanResponse,
  VoiceCommandResponse,
  IncidentNarrationResponse,
  NebiusAuditResponse,
  LedgerMetricsResponse,
  AccessibilityStandardResponse,
  MonteCarloSummaryResponse,
  SensitivitySweepResponse,
  DepthBenchmarkResponse,
} from '../types'

const API_BASE = ''

async function handleResponse<T>(res: Response, fallbackDesc: string): Promise<T> {
  if (!res.ok) {
    const errorText = await res.text().catch(() => res.statusText)
    throw new Error(`${fallbackDesc} failed (${res.status}): ${errorText}`)
  }
  return res.json() as Promise<T>
}

function parseSimulationCondition(raw: any): SimulationConditionResult {
  if (!raw) {
    return {
      trajectory: [],
      summary: { collision: false, peak_alpha: 0, duration_s: 0 },
    }
  }

  // If already array of points
  if (Array.isArray(raw.trajectory) && raw.trajectory.length > 0) {
    const rawSum = raw.summary || {}
    return {
      trajectory: raw.trajectory,
      summary: {
        status: rawSum.status || (rawSum.passed_door ? 'PASSED' : rawSum.collision ? 'COLLISION' : 'RUNNING'),
        passed: Boolean(rawSum.passed_door ?? !rawSum.collision),
        passed_door: Boolean(rawSum.passed_door),
        collision: Boolean(rawSum.collision),
        min_clearance_m: rawSum.min_door_clearance_m ?? rawSum.min_clearance_m ?? 0,
        min_door_clearance_m: rawSum.min_door_clearance_m,
        peak_alpha: rawSum.peak_alpha ?? 0,
        duration_s: rawSum.duration_s ?? 0,
        scrape_count: rawSum.scrape_count ?? 0,
        reason: rawSum.reason,
      },
    }
  }

  // Columnar format (t: number[], x: number[], y: number[]...)
  const tArr: number[] = raw.t || []
  const xArr: number[] = raw.x || []
  const yArr: number[] = raw.y || []
  const phiArr: number[] = raw.phi_deg || raw.phi || []
  const vArr: number[] = raw.v || []
  const alphaArr: number[] = raw.alpha || []
  const riskArr: number[] = raw.risk || []
  const clearLArr: number[] = raw.clear_left || raw.clear_l || []
  const clearRArr: number[] = raw.clear_right || raw.clear_r || []
  const frontRangeArr: number[] = raw.front_range || []
  const aebArr: any[] = raw.aeb || []

  const n = tArr.length
  const trajectory: TrajectoryPoint[] = []

  for (let i = 0; i < n; i++) {
    trajectory.push({
      t: tArr[i] ?? 0,
      x: xArr[i] ?? 0,
      y: yArr[i] ?? 0,
      phi: phiArr[i] ?? 90,
      v: vArr[i] ?? 0.8,
      alpha: alphaArr[i] ?? 0,
      risk: riskArr[i] ?? 0,
      clear_left: clearLArr[i] ?? 0.5,
      clear_right: clearRArr[i] ?? 0.5,
      front_range: frontRangeArr[i] ?? 4.0,
      aeb: Boolean(aebArr[i]),
    })
  }

  const rawSum = raw.summary || {}
  const summary: SimulationSummary = {
    status: rawSum.status || (rawSum.passed_door ? 'PASSED' : rawSum.collision ? 'COLLISION' : 'RUNNING'),
    passed: Boolean(rawSum.passed_door ?? !rawSum.collision),
    passed_door: Boolean(rawSum.passed_door),
    collision: Boolean(rawSum.collision),
    min_clearance_m: rawSum.min_door_clearance_m ?? rawSum.min_clearance_m ?? 0,
    min_door_clearance_m: rawSum.min_door_clearance_m,
    peak_alpha: rawSum.peak_alpha ?? 0,
    duration_s: rawSum.duration_s ?? (tArr[n - 1] || 0),
    scrape_count: rawSum.scrape_count ?? 0,
    reason: rawSum.reason,
  }

  return { trajectory, summary }
}

export const api = {
  async getMonteCarloSummary(): Promise<MonteCarloSummaryResponse> {
    const res = await fetch(`${API_BASE}/api/monte-carlo/summary`)
    return handleResponse<MonteCarloSummaryResponse>(res, 'Fetch Monte Carlo summary')
  },

  async getSensitivitySweep(): Promise<SensitivitySweepResponse> {
    const res = await fetch(`${API_BASE}/api/monte-carlo/sensitivity`)
    return handleResponse<SensitivitySweepResponse>(res, 'Fetch sensitivity sweep')
  },

  async getDepthBenchmark(): Promise<DepthBenchmarkResponse> {
    const res = await fetch(`${API_BASE}/api/depth-benchmark/results`)
    return handleResponse<DepthBenchmarkResponse>(res, 'Fetch depth benchmark')
  },

  async simulateClosedLoop(params: {
    drift_deg: number
    door_width_m: number
    tremor_deg: number
    duration_s?: number
    reaction_delay_s?: number
    visual_gain?: number
    fatigue_rate?: number
  }): Promise<ClosedLoopResponse> {
    const res = await fetch(`${API_BASE}/api/simulate/closed-loop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        duration_s: 9.0,
        reaction_delay_s: 0.35,
        visual_gain: 1.2,
        fatigue_rate: 0.05,
        ...params,
      }),
    })
    const raw = await handleResponse<any>(res, 'Simulate closed-loop')
    return {
      params: raw.params || params,
      unassisted: parseSimulationCondition(raw.unassisted),
      corrective: parseSimulationCondition(raw.corrective || raw.unassisted),
      waylo: parseSimulationCondition(raw.waylo),
    }
  },

  async getPerceptionScan(params: {
    x?: number
    y?: number
    heading?: number
    door_width_m?: number
    door_y?: number
  }): Promise<PerceptionScanResponse> {
    const res = await fetch(`${API_BASE}/api/perception/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    return handleResponse<PerceptionScanResponse>(res, 'Perception scan')
  },

  async sendVoiceCommand(utterance: string): Promise<VoiceCommandResponse> {
    const res = await fetch(`${API_BASE}/api/v1/voice-command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: utterance, utterance }),
    })
    return handleResponse<VoiceCommandResponse>(res, 'Voice command')
  },

  async narrateIncident(payload: {
    event_type?: string
    peak_risk?: number
    speed_mps?: number
    min_clearance_m?: number
    alpha?: number
    user_profile?: string
  }): Promise<IncidentNarrationResponse> {
    const event = {
      event_type: 'doorway_entry_assist',
      peak_risk: 0.85,
      speed_mps: 0.9,
      min_clearance_m: 0.06,
      alpha: 0.68,
      user_profile: 'Tremor 2.0 deg, Drift 15.0 deg',
      ...payload,
    }
    const res = await fetch(`${API_BASE}/api/v1/narrate-incident`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, ...event }),
    })
    return handleResponse<IncidentNarrationResponse>(res, 'Narrate incident')
  },

  async getLedgerMetrics(): Promise<LedgerMetricsResponse> {
    const res = await fetch(`${API_BASE}/api/v1/ledger/metrics`)
    return handleResponse<LedgerMetricsResponse>(res, 'Fetch ledger metrics')
  },

  async getNebiusAudit(): Promise<NebiusAuditResponse> {
    const res = await fetch(`${API_BASE}/api/nebius/audit`)
    return handleResponse<NebiusAuditResponse>(res, 'Fetch Nebius audit')
  },

  async getAccessibilityStandard(region: string): Promise<AccessibilityStandardResponse> {
    const res = await fetch(`${API_BASE}/api/accessibility/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ region }),
    })
    return handleResponse<AccessibilityStandardResponse>(res, 'Accessibility standard search')
  },
}
