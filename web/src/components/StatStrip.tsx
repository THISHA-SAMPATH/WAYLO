import React from 'react'
import type { MonteCarloSummaryResponse } from '../types'
import { AlertCircle, TrendingDown, CheckCircle2, ShieldAlert } from 'lucide-react'

interface StatStripProps {
  summary: MonteCarloSummaryResponse | null
  loading: boolean
  error: string | null
}

function pct(val: number | undefined): string {
  if (val === undefined || isNaN(val)) return '—'
  return `${(val * 100).toFixed(1)}%`
}

function ciPct(ci: [number, number] | undefined): string {
  if (!ci || ci.length < 2) return ''
  return `[${(ci[0] * 100).toFixed(1)}%, ${(ci[1] * 100).toFixed(1)}%]`
}

export const StatStrip: React.FC<StatStripProps> = ({ summary, loading, error }) => {
  if (loading) {
    return (
      <section className="py-12 border-y border-[#14201B]/10 bg-white/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 bg-[#F4F2EC] rounded-3xl p-6"></div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (error || !summary) {
    return (
      <section className="py-8 border-y border-[#14201B]/10 bg-white/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <p className="text-sm">
              Unable to load live Monte Carlo summary ({error || 'Data pending'}). Numbers will render dynamically once the backend server responds.
            </p>
          </div>
        </div>
      </section>
    )
  }

  const { overall, by_door_width } = summary
  const door081 = by_door_width?.['0.81']

  return (
    <section className="py-16 md:py-24 border-y border-[#14201B]/10 bg-white/60 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#14201B]/5 text-xs font-semibold text-[#17352B] mb-2">
              <span className="w-2 h-2 rounded-full bg-[#F26B3A]"></span>
              <span>Rigorous Monte Carlo Benchmark</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#14201B]">
              Empirical Safety <span className="marker-highlight">Gains</span>
            </h2>
          </div>
          <p className="text-xs sm:text-sm font-mono text-[#5B6B63] bg-[#F4F2EC] px-3.5 py-1.5 rounded-xl border border-[#14201B]/5">
            Simulation, N={summary.metadata.n_trials.toLocaleString()} · 95% Wilson Score CIs
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          {/* Card 1: Overall Collision Rate */}
          <div className="rounded-3xl bg-white border border-[#14201B]/10 p-6 sm:p-8 shadow-card hover:shadow-soft transition-all space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-[#5B6B63] uppercase tracking-wider">
              <span>Overall Collision Rate</span>
              <ShieldAlert className="w-4 h-4 text-[#C2410C]" />
            </div>

            <div className="flex items-baseline gap-2">
              <span className="text-4xl sm:text-5xl font-extrabold text-[#17352B] tracking-tight">
                {pct(overall.waylo.collision_rate)}
              </span>
              <span className="text-xs font-mono text-[#1F7A4D] font-bold">
                WAYLO {ciPct(overall.waylo.collision_ci_95)}
              </span>
            </div>

            <div className="pt-3 border-t border-[#14201B]/5 space-y-2 text-xs">
              <div className="flex justify-between items-center text-[#5B6B63]">
                <span>Unassisted driver (red path):</span>
                <span className="font-mono font-semibold text-[#C2410C]">
                  {pct(overall.unassisted.collision_rate)} {ciPct(overall.unassisted.collision_ci_95)}
                </span>
              </div>
              <div className="flex justify-between items-center text-[#5B6B63]">
                <span>Corrective baseline (deadband):</span>
                <span className="font-mono font-semibold text-[#5B6B63]">
                  {pct(overall.corrective.collision_rate)} {ciPct(overall.corrective.collision_ci_95)}
                </span>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-[#F4F2EC] text-[11px] text-[#5B6B63] flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-[#1F7A4D] shrink-0" />
              <span>Reduced collision likelihood by {(overall.unassisted.collision_rate / overall.waylo.collision_rate).toFixed(0)}× over unassisted control</span>
            </div>
          </div>

          {/* Card 2: Narrowest ADA Doorway (0.81 m) */}
          <div className="rounded-3xl bg-white border border-[#14201B]/10 p-6 sm:p-8 shadow-card hover:shadow-soft transition-all space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-[#5B6B63] uppercase tracking-wider">
              <span>0.81 m Door Pass Rate</span>
              <CheckCircle2 className="w-4 h-4 text-[#1F7A4D]" />
            </div>

            <div className="flex items-baseline gap-2">
              <span className="text-4xl sm:text-5xl font-extrabold text-[#17352B] tracking-tight">
                {door081 ? pct(door081.waylo.pass_rate) : '—'}
              </span>
              <span className="text-xs font-mono text-[#1F7A4D] font-bold">
                {door081 ? ciPct(door081.waylo.pass_ci_95) : ''}
              </span>
            </div>

            <div className="pt-3 border-t border-[#14201B]/5 space-y-2 text-xs">
              <div className="flex justify-between items-center text-[#5B6B63]">
                <span>Unassisted driver:</span>
                <span className="font-mono font-semibold text-[#C2410C]">
                  {door081 ? pct(door081.unassisted.pass_rate) : '—'}
                </span>
              </div>
              <div className="flex justify-between items-center text-[#5B6B63]">
                <span>Corrective baseline:</span>
                <span className="font-mono font-semibold text-[#5B6B63]">
                  {door081 ? pct(door081.corrective.pass_rate) : '—'}
                </span>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-[#F4F2EC] text-[11px] text-[#5B6B63] flex items-center gap-2">
              <span className="font-semibold text-[#17352B]">ADA Minimum:</span>
              <span>32-inch clear opening (0.813 m) requires sub-centimeter steering precision</span>
            </div>
          </div>

          {/* Card 3: Minimum Clearance Margin (Passed Runs) */}
          <div className="rounded-3xl bg-white border border-[#14201B]/10 p-6 sm:p-8 shadow-card hover:shadow-soft transition-all space-y-4">
            <div className="flex items-center justify-between text-xs font-semibold text-[#5B6B63] uppercase tracking-wider">
              <span>Mean Passed Clearance</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] bg-[#E3F26D] text-[#17352B] font-bold">
                +{(overall.waylo.min_clearance_passed_mean * 100).toFixed(1)} cm
              </span>
            </div>

            <div className="flex items-baseline gap-2">
              <span className="text-4xl sm:text-5xl font-extrabold text-[#17352B] tracking-tight">
                {(overall.waylo.min_clearance_passed_mean * 100).toFixed(1)}
              </span>
              <span className="text-lg font-semibold text-[#5B6B63]">cm safety margin</span>
            </div>

            <div className="pt-3 border-t border-[#14201B]/5 space-y-2 text-xs">
              <div className="flex justify-between items-center text-[#5B6B63]">
                <span>Unassisted passed runs:</span>
                <span className="font-mono font-semibold text-[#5B6B63]">
                  {(overall.unassisted.min_clearance_passed_mean * 100).toFixed(1)} cm (grazing threshold)
                </span>
              </div>
              <div className="flex justify-between items-center text-[#5B6B63]">
                <span>Corrective baseline:</span>
                <span className="font-mono font-semibold text-[#5B6B63]">
                  {(overall.corrective.min_clearance_passed_mean * 100).toFixed(1)} cm
                </span>
              </div>
            </div>

            <div className="p-2.5 rounded-xl bg-[#F4F2EC] text-[11px] text-[#5B6B63] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#1F7A4D]"></span>
              <span>Active DWA centering prevents door frame scrapes and scuffs</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
