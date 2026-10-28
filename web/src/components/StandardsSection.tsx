import React, { useState, useEffect } from 'react'
import { Globe, ExternalLink, Bookmark, ArrowUpRight, AlertCircle } from 'lucide-react'
import { api } from '../api/client'
import type { AccessibilityStandardResponse } from '../types'

interface StandardsSectionProps {
  onApplyDoorWidth?: (widthM: number) => void
}

export const StandardsSection: React.FC<StandardsSectionProps> = ({ onApplyDoorWidth }) => {
  const [selectedRegion, setSelectedRegion] = useState<string>('US')
  const [loading, setLoading] = useState<boolean>(false)
  const [data, setData] = useState<AccessibilityStandardResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const regions = [
    { code: 'US', label: 'United States (ADA 2010)' },
    { code: 'UK', label: 'United Kingdom (BS 8300)' },
    { code: 'EU', label: 'European Union (EN 301 549)' },
    { code: 'Canada', label: 'Canada (CSA B651)' },
    { code: 'Australia', label: 'Australia (AS 1428.1)' },
    { code: 'Japan', label: 'Japan (Barrier-Free Act)' },
  ]

  const fetchStandard = async (region: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getAccessibilityStandard(region)
      setData(res)
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch standards')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStandard(selectedRegion)
  }, [selectedRegion])

  const isLive = data?.source === 'tavily_search'

  return (
    <section id="standards" className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="rounded-3xl bg-white border border-[#14201B]/10 p-8 sm:p-12 shadow-soft-lg space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-[#14201B]/10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#17352B]/5 text-xs font-semibold text-[#17352B] mb-2">
              <Globe className="w-3.5 h-3.5 text-[#17352B]" />
              <span>International Accessibility Standards</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#14201B]">
              Real-World Doorway <span className="marker-highlight">Standards</span>
            </h2>
            <p className="text-base text-[#5B6B63] mt-1 max-w-2xl">
              Cross-referenced against global regulatory baselines via Tavily live search. Benchmark how WAYLO performs against mandatory door clearances.
            </p>
          </div>

          {/* Region Selector Dropdown */}
          <div className="flex items-center gap-3">
            <label htmlFor="select-region" className="text-xs font-semibold text-[#5B6B63] uppercase">
              Select Jurisdiction:
            </label>
            <select
              id="select-region"
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="px-4 py-2.5 rounded-xl border border-[#14201B]/15 bg-[#F4F2EC] text-[#14201B] font-semibold text-sm focus:outline-none focus:ring-2 focus:ring-[#17352B] min-h-[44px]"
            >
              {regions.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Content Box */}
        {error ? (
          <div className="p-4 rounded-2xl bg-amber-50 text-amber-900 border border-amber-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : loading ? (
          <div className="h-48 rounded-2xl bg-[#F4F2EC] animate-pulse flex items-center justify-center text-xs text-[#5B6B63]">
            Querying accessibility regulatory database...
          </div>
        ) : data ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left Column: Metrics & Standard Code (5 cols) */}
            <div className="lg:col-span-5 p-6 rounded-2xl bg-[#F4F2EC] border border-[#14201B]/5 space-y-4">
              <div className="flex justify-between items-center">
                <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold bg-[#17352B] text-white">
                  {data.standard_code}
                </span>

                {/* Source Badge */}
                <span
                  id="standards-source-badge"
                  className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 border ${
                    isLive
                      ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
                      : 'bg-amber-50 text-amber-900 border-amber-300'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
                  <span>{isLive ? 'Live (Tavily search)' : 'Cached fallback'}</span>
                </span>
              </div>

              <div>
                <p className="text-xs text-[#5B6B63] uppercase font-semibold">Statutory Minimum Width</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-4xl font-extrabold text-[#17352B] tracking-tight font-mono">
                    {data.door_width_min_m.toFixed(3)} m
                  </span>
                  <span className="text-sm text-[#5B6B63]">
                    ({(data.door_width_min_m * 39.3701).toFixed(1)} inches)
                  </span>
                </div>
              </div>

              <div>
                <p className="text-xs text-[#5B6B63] uppercase font-semibold">Recommended Comfortable Clearance</p>
                <p className="text-xl font-bold text-[#14201B] font-mono mt-0.5">
                  {data.clearance_recommended_m.toFixed(2)} m
                </p>
              </div>

              {onApplyDoorWidth && (
                <button
                  onClick={() => onApplyDoorWidth(data.door_width_min_m)}
                  className="w-full mt-2 py-3 rounded-xl bg-white border border-[#14201B]/15 hover:bg-[#E3F26D]/30 text-xs font-bold text-[#14201B] flex items-center justify-center gap-2 transition min-h-[44px]"
                >
                  <span>Test this standard in 3D simulator</span>
                  <ArrowUpRight className="w-4 h-4 text-[#17352B]" />
                </button>
              )}
            </div>

            {/* Right Column: Regulatory Guidance Excerpt (7 cols) */}
            <div className="lg:col-span-7 space-y-4">
              <h3 className="text-xl font-bold text-[#14201B] flex items-center gap-2">
                <Bookmark className="w-5 h-5 text-[#F26B3A]" />
                <span>{data.title}</span>
              </h3>

              <div className="p-5 rounded-2xl bg-[#F4F2EC]/60 border border-[#14201B]/10 text-sm text-[#14201B] leading-relaxed">
                "{data.content}"
              </div>

              <div className="flex items-center justify-between text-xs text-[#5B6B63] pt-2">
                <span>Jurisdiction: {data.region} regulatory baseline</span>
                {data.url && (
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#17352B] hover:underline font-semibold flex items-center gap-1 min-h-[36px]"
                  >
                    <span>Official Standard Source</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-[#5B6B63]">Select a region above to query doorway standards.</p>
        )}
      </div>
    </section>
  )
}
