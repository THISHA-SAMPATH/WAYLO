import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import App from '../App'

// Mock global fetch
const mockMonteCarloSummary = {
  metadata: {
    n_trials: 1000,
    conditions: ['unassisted', 'corrective', 'waylo'],
    door_widths: [0.81, 0.85, 0.9, 1.0, 1.2],
    seed: 42,
  },
  overall: {
    unassisted: {
      collision_rate: 0.477,
      collision_ci_95: [0.446, 0.508],
      pass_rate: 0.523,
      pass_ci_95: [0.492, 0.554],
      min_clearance_passed_mean: 0.0212,
      min_clearance_passed_std: 0.015,
      n: 1000,
    },
    corrective: {
      collision_rate: 0.408,
      collision_ci_95: [0.378, 0.439],
      pass_rate: 0.592,
      pass_ci_95: [0.561, 0.622],
      min_clearance_passed_mean: 0.0381,
      min_clearance_passed_std: 0.021,
      n: 1000,
    },
    waylo: {
      collision_rate: 0.029,
      collision_ci_95: [0.02, 0.041],
      pass_rate: 0.971,
      pass_ci_95: [0.959, 0.98],
      min_clearance_passed_mean: 0.0634,
      min_clearance_passed_std: 0.028,
      n: 1000,
    },
  },
  by_door_width: {
    '0.81': {
      door_width_m: 0.81,
      unassisted: {
        collision_rate: 0.535,
        collision_ci_95: [0.466, 0.603],
        pass_rate: 0.465,
        pass_ci_95: [0.397, 0.534],
        min_clearance_passed_mean: 0.018,
        min_clearance_passed_std: 0.012,
        n: 200,
      },
      corrective: {
        collision_rate: 0.485,
        collision_ci_95: [0.417, 0.554],
        pass_rate: 0.515,
        pass_ci_95: [0.446, 0.583],
        min_clearance_passed_mean: 0.029,
        min_clearance_passed_std: 0.018,
        n: 200,
      },
      waylo: {
        collision_rate: 0.145,
        collision_ci_95: [0.103, 0.201],
        pass_rate: 0.855,
        pass_ci_95: [0.799, 0.897],
        min_clearance_passed_mean: 0.048,
        min_clearance_passed_std: 0.022,
        n: 200,
      },
    },
  },
}

const mockClosedLoop = {
  params: {
    drift_deg: 14.0,
    door_width_m: 1.1,
    tremor_deg: 2.0,
    duration_s: 9.0,
  },
  unassisted: {
    trajectory: [
      { t: 0, x: 0, y: 0, phi: 90, v: 0.8, alpha: 0, risk: 0, clear_left: 0.55, clear_right: 0.55, front_range: 4.5, aeb: false },
      { t: 4.5, x: 0.4, y: 4.5, phi: 78, v: 0.8, alpha: 0, risk: 0.9, clear_left: 0.95, clear_right: 0.02, front_range: 0.1, aeb: false },
    ],
    summary: {
      status: 'COLLISION',
      passed: false,
      collision: true,
      min_clearance_m: 0.02,
      peak_alpha: 0,
      duration_s: 4.8,
      scrape_count: 1,
    },
  },
  corrective: {
    trajectory: [],
    summary: { status: 'PASSED', passed: true, collision: false, min_clearance_m: 0.04, peak_alpha: 0.5, duration_s: 5.2 },
  },
  waylo: {
    trajectory: [
      { t: 0, x: 0, y: 0, phi: 90, v: 0.8, alpha: 0, risk: 0, clear_left: 0.55, clear_right: 0.55, front_range: 4.5, aeb: false },
      { t: 4.5, x: 0.05, y: 4.5, phi: 89, v: 0.75, alpha: 0.62, risk: 0.4, clear_left: 0.5, clear_right: 0.5, front_range: 0.5, aeb: false },
    ],
    summary: {
      status: 'PASSED',
      passed: true,
      collision: false,
      min_clearance_m: 0.072,
      peak_alpha: 0.62,
      duration_s: 5.5,
    },
  },
}

const mockVoiceResponse = {
  speed_cap_mps: 0.5,
  clearance_margin_m: 0.05,
  door_mode: 'conservative',
  intent_summary: 'Reduced speed cap and added extra 5cm door margin',
  source: 'offline_deterministic_fallback',
  model: 'offline-safety-rules',
}

const mockLedgerMetrics = {
  independence_ratio: 0.85,
  near_misses_avoided: 18,
  scrapes_recorded: 0,
  collisions_recorded: 0,
  privacy_audit: {
    images_stored: 0,
    cloud_telemetry_in_loop: 0,
    local_control_hz: 50,
    cloud_audit_isolated: true,
  },
  cost_avoidance: {
    estimated_dollars: 1420.0,
    formula: 'near_misses * $75',
    label: 'assumption-based',
  },
}

const mockStandard = {
  region: 'US',
  door_width_min_m: 0.815,
  clearance_recommended_m: 0.85,
  source: 'cached_fallback',
  title: 'ADA Standards Section 404.2.3',
  url: 'https://www.ada.gov',
  content: 'Door openings shall provide a clear width of 32 inches minimum.',
  standard_code: 'ADA 2010 Section 404.2.3',
}

// Mock ThreeScene Canvas because WebGL Canvas is not implemented in JSDOM
vi.mock('../components/ThreeScene', () => ({
  ThreeScene: () => <div data-testid="mock-three-scene">3D Scene Canvas</div>,
}))

describe('WAYLO Web App Smoke Tests', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/api/monte-carlo/summary')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockMonteCarloSummary) })
      }
      if (url.includes('/api/simulate/closed-loop')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockClosedLoop) })
      }
      if (url.includes('/api/v1/voice-command')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockVoiceResponse) })
      }
      if (url.includes('/api/v1/ledger/metrics')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockLedgerMetrics) })
      }
      if (url.includes('/api/accessibility/search')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockStandard) })
      }
      if (url.includes('/api/monte-carlo/sensitivity')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'SUCCESS',
              rows: [
                {
                  sweep_param: 'reaction_delay_s',
                  sweep_value: '0.35',
                  condition: 'waylo',
                  collision_rate: '0.029',
                  pass_rate: '0.971',
                  min_clearance_mean: '0.063',
                  notes: 'Baseline reaction delay',
                },
              ],
            }),
        })
      }
      if (url.includes('/api/depth-benchmark/results')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              total_frames: 20,
              detected_count: 19,
              failed_frames: [14],
              mean_door_width_error_m: 0.038,
              max_door_width_error_m: 0.082,
              frames: [],
            }),
        })
      }
      if (url.includes('/api/nebius/audit')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'SUCCESS',
              total_calls: 1,
              token_factory_verified: true,
              calls: [],
            }),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    }))
  })

  it('1. Page loads and renders the Hero headline with marker highlight', async () => {
    render(<App />)

    // Headline check
    const headline = await screen.findByRole('heading', { level: 1 })
    expect(headline).toBeInTheDocument()
    expect(headline.textContent).toContain('Your world. Your way.')

    // Primary and secondary CTAs
    expect(screen.getByText('Try the doorway demo')).toBeInTheDocument()
    expect(screen.getByText('See the evidence')).toBeInTheDocument()

    // Floating badges
    expect(screen.getByText('0 Images')).toBeInTheDocument()
    expect(screen.getByText('Runs on-device')).toBeInTheDocument()
  })

  it('2. Stat cards dynamically render empirical Monte Carlo figures', async () => {
    render(<App />)

    // Overall WAYLO collision rate 2.9%
    expect(await screen.findByText('2.9%')).toBeInTheDocument()
    // 0.81m door pass rate 85.5%
    expect(screen.getByText('85.5%')).toBeInTheDocument()
    // Mean clearance 6.3 cm
    expect(screen.getByText('6.3')).toBeInTheDocument()
  })

  it('3. Voice compilation displays Fallback (offline) badge when model is offline', async () => {
    render(<App />)

    const voiceInput = await screen.findByLabelText('Voice command text input')
    fireEvent.change(voiceInput, { target: { value: 'Slow down through narrow doors' } })

    const compileBtn = screen.getByRole('button', { name: /send voice command/i })
    fireEvent.click(compileBtn)

    // Offline fallback badge
    expect(await screen.findByText('Fallback (offline)')).toBeInTheDocument()
    // Safety layer approved badge
    expect(await screen.findByText('Approved by safety layer')).toBeInTheDocument()
    // Result parameter chip
    expect(await screen.findByText(/Speed cap: 0.50 m\/s/i)).toBeInTheDocument()
    expect(await screen.findByText(/Extra margin: \+5 cm/i)).toBeInTheDocument()
  })

  it('4. Simulation controls trigger closed-loop API and display telemetry', async () => {
    render(<App />)

    // Wait for initial mount simulation to complete so button says "Run Simulation"
    const runBtn = await screen.findByRole('button', { name: /run simulation/i }, { timeout: 3000 })
    fireEvent.click(runBtn)

    expect(await screen.findByText('SAFE PASS')).toBeInTheDocument()
    expect(await screen.findByText('+7.2 cm')).toBeInTheDocument()
    expect(await screen.findByText('COLLISION')).toBeInTheDocument()
  })

  it('5. Switches to Evidence page and displays N=1000 Monte Carlo and failure cases', async () => {
    render(<App />)

    const evidenceNavBtn = await screen.findByRole('button', { name: /evidence \(n=1000\)/i })
    fireEvent.click(evidenceNavBtn)

    expect(await screen.findByText('Scientific')).toBeInTheDocument()
    expect(screen.getByText('Doorway Passage & Collision Table (N=1000)')).toBeInTheDocument()
    expect(screen.getByText('Full Audit of All 29 WAYLO Failure Cases')).toBeInTheDocument()
    expect(screen.getByText(/Preliminary Real Depth-Image Benchmark/i)).toBeInTheDocument()
  })
})
