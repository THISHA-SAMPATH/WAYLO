import type {
  ClosedLoopResponse,
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
    return handleResponse<ClosedLoopResponse>(res, 'Simulate closed-loop')
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
      body: JSON.stringify({ utterance }),
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
    const res = await fetch(`${API_BASE}/api/v1/narrate-incident`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event_type: 'doorway_entry_assist',
        peak_risk: 0.85,
        speed_mps: 0.9,
        min_clearance_m: 0.06,
        alpha: 0.68,
        user_profile: 'Tremor 2.0 deg, Drift 15.0 deg',
        ...payload,
      }),
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
