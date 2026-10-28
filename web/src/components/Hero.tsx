import { ArrowRight, ShieldCheck, Cpu, Database } from 'lucide-react'

interface HeroProps {
  onTryDemo: () => void
  onSeeEvidence: () => void
}

export const Hero: React.FC<HeroProps> = ({ onTryDemo, onSeeEvidence }) => {
  return (
    <section className="relative pt-12 pb-20 md:pt-20 md:pb-28 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: SaaS Headline and CTAs */}
          <div className="lg:col-span-7 space-y-8">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-[#14201B]/10 shadow-sm text-xs font-semibold text-[#17352B]">
              <span className="w-2 h-2 rounded-full bg-[#1F7A4D]"></span>
              <span>Physical AI Shared-Autonomy Hackathon Entry</span>
              <span className="text-[#5B6B63]">·</span>
              <span className="text-[#5B6B63]">Zero Cloud Telemetry in Loop</span>
            </div>

            <h1 className="text-4xl sm:text-6xl lg:text-[70px] font-bold tracking-tight text-[#14201B] leading-[1.08]">
              Your world. Your <span className="marker-highlight">way</span>.
            </h1>

            <p className="text-lg sm:text-xl text-[#5B6B63] max-w-2xl leading-relaxed">
              Doorway copilot for power wheelchairs. Continuous shared-autonomy blending that preserves driver intent while guaranteeing frame clearance.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={onTryDemo}
                id="btn-try-demo"
                className="px-7 py-4 rounded-2xl bg-[#17352B] hover:bg-[#1f473a] text-white font-semibold text-base transition-all shadow-md hover:shadow-lg flex items-center gap-3 min-h-[52px] group"
              >
                <span>Try the doorway demo</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform text-[#E3F26D]" />
              </button>

              <button
                onClick={onSeeEvidence}
                id="btn-see-evidence"
                className="px-7 py-4 rounded-2xl bg-white hover:bg-[#F4F2EC] text-[#14201B] border border-[#14201B]/15 font-semibold text-base transition-all shadow-sm hover:shadow min-h-[52px]"
              >
                See the evidence
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-6 pt-4 text-xs sm:text-sm text-[#5B6B63]">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-[#1F7A4D]" />
                <span>Audited on Nebius Nemotron</span>
              </div>
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-[#17352B]" />
                <span>50 Hz Local Dynamic Window (DWA)</span>
              </div>
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-[#F26B3A]" />
                <span>Tavily ADA/BS/EN Standards</span>
              </div>
            </div>
          </div>

          {/* Right Column: Hero Visual with Live Mini Preview & Floating Chips */}
          <div className="lg:col-span-5 relative">
            <div className="relative mx-auto w-full max-w-md lg:max-w-none">
              {/* Background ambient glow */}
              <div className="absolute -inset-2 bg-gradient-to-tr from-[#E3F26D]/30 to-[#F26B3A]/20 rounded-3xl blur-2xl opacity-70"></div>

              {/* Main Card */}
              <div className="relative rounded-3xl bg-white border border-[#14201B]/10 p-6 sm:p-8 shadow-soft-lg space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-[#14201B]/5">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-[#1F7A4D]"></span>
                    <span className="font-semibold text-sm text-[#14201B]">Live Twin Telemetry</span>
                  </div>
                  <span className="text-xs font-mono text-[#5B6B63] bg-[#F4F2EC] px-2.5 py-1 rounded-md">
                    DOORWAY 0.85m
                  </span>
                </div>

                {/* Simulated Mini Canvas / Top-down schematic preview */}
                <div className="relative h-64 bg-[#14201B] rounded-2xl overflow-hidden p-4 border border-[#14201B]/10 flex flex-col justify-between">
                  <div className="flex justify-between items-center text-[11px] font-mono text-emerald-400">
                    <span>LiDAR 61 RAYS</span>
                    <span>α = 0.42 BLEND</span>
                  </div>

                  {/* Visual SVG Doorway & Path Animation */}
                  <svg viewBox="0 0 300 180" className="w-full h-36" fill="none" xmlns="http://www.w3.org/2000/svg">
                    {/* Walls and Door */}
                    <line x1="20" y1="60" x2="110" y2="60" stroke="#5B6B63" strokeWidth="6" strokeLinecap="round" />
                    <line x1="190" y1="60" x2="280" y2="60" stroke="#5B6B63" strokeWidth="6" strokeLinecap="round" />
                    <circle cx="110" cy="60" r="4" fill="#E3F26D" />
                    <circle cx="190" cy="60" r="4" fill="#E3F26D" />
                    <text x="150" y="52" fill="#E3F26D" fontSize="10" textAnchor="middle" fontFamily="monospace">DOOR OPENING 0.85m</text>

                    {/* Unassisted Path (Red Dashed - heading to left post) */}
                    <path
                      d="M 150 160 Q 140 120 110 64"
                      stroke="#C2410C"
                      strokeWidth="2.5"
                      strokeDasharray="5 4"
                      opacity="0.85"
                    />
                    <circle cx="110" cy="64" r="5" fill="#C2410C" />
                    <text x="75" y="85" fill="#C2410C" fontSize="9" fontFamily="monospace">Unassisted Collision</text>

                    {/* WAYLO Blended Path (Green Solid - smoothly centered) */}
                    <path
                      d="M 150 160 Q 148 110 150 60 L 150 20"
                      stroke="#1F7A4D"
                      strokeWidth="3.5"
                      strokeLinecap="round"
                    />
                    <rect x="142" y="50" width="16" height="20" rx="3" fill="#E3F26D" stroke="#17352B" strokeWidth="1.5" />
                    <text x="210" y="35" fill="#1F7A4D" fontSize="10" fontWeight="bold" fontFamily="monospace">WAYLO Safe Entry</text>
                  </svg>

                  <div className="flex justify-between items-center text-[11px] font-mono text-[#5B6B63]">
                    <span className="text-white/60">Heading drift: +15°</span>
                    <span className="text-[#E3F26D]">Passed: +7.2cm clearance</span>
                  </div>
                </div>

                {/* Floating Chips */}
                <div className="grid grid-cols-3 gap-2 pt-1">
                  <div className="p-2.5 rounded-xl bg-[#F4F2EC] border border-[#14201B]/5 text-center">
                    <p className="text-xs font-bold text-[#14201B]">0 Images</p>
                    <p className="text-[10px] text-[#5B6B63]">Stored or streamed</p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#F4F2EC] border border-[#14201B]/5 text-center">
                    <p className="text-xs font-bold text-[#1F7A4D]">Runs on-device</p>
                    <p className="text-[10px] text-[#5B6B63]">50 Hz local loop</p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#F4F2EC] border border-[#14201B]/5 text-center">
                    <p className="text-xs font-bold text-[#F26B3A]">Simulation</p>
                    <p className="text-[10px] text-[#5B6B63]">N=1000 benchmark</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
