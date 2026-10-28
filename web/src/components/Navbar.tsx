import { BarChart3, Activity } from 'lucide-react'

interface NavbarProps {
  currentTab: 'app' | 'evidence'
  onSelectTab: (tab: 'app' | 'evidence') => void
  onScrollToSection?: (sectionId: string) => void
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onSelectTab, onScrollToSection }) => {
  return (
    <header className="sticky top-0 z-50 w-full bg-[#F4F2EC]/90 backdrop-blur-md border-b border-[#14201B]/10 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => onSelectTab('app')}>
          <div className="w-10 h-10 rounded-xl bg-[#17352B] flex items-center justify-center text-[#E3F26D] font-bold text-xl shadow-sm">
            W
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-2xl tracking-tight text-[#14201B]">WAYLO</span>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide bg-[#17352B]/10 text-[#17352B] uppercase">
                Copilot
              </span>
            </div>
            <p className="text-xs text-[#5B6B63] hidden sm:block">Physical AI Wheelchair Shared-Autonomy</p>
          </div>
        </div>

        {/* View Switcher / Nav Links */}
        <nav className="flex items-center gap-2 sm:gap-4" aria-label="Main Navigation">
          {currentTab === 'app' ? (
            <div className="hidden md:flex items-center gap-1 text-sm font-medium text-[#5B6B63]">
              <button
                onClick={() => onScrollToSection?.('demo')}
                className="px-3 py-2 rounded-lg hover:text-[#14201B] hover:bg-black/5 transition min-h-[48px]"
              >
                3D Twin Demo
              </button>
              <button
                onClick={() => onScrollToSection?.('voice')}
                className="px-3 py-2 rounded-lg hover:text-[#14201B] hover:bg-black/5 transition min-h-[48px]"
              >
                Voice Copilot
              </button>
              <button
                onClick={() => onScrollToSection?.('ledger')}
                className="px-3 py-2 rounded-lg hover:text-[#14201B] hover:bg-black/5 transition min-h-[48px]"
              >
                Caregiver Ledger
              </button>
              <button
                onClick={() => onScrollToSection?.('standards')}
                className="px-3 py-2 rounded-lg hover:text-[#14201B] hover:bg-black/5 transition min-h-[48px]"
              >
                Standards
              </button>
            </div>
          ) : null}

          <div className="flex items-center bg-[#14201B]/5 p-1 rounded-2xl border border-[#14201B]/10">
            <button
              onClick={() => onSelectTab('app')}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all min-h-[44px] flex items-center gap-2 ${
                currentTab === 'app'
                  ? 'bg-[#17352B] text-white shadow-sm'
                  : 'text-[#5B6B63] hover:text-[#14201B]'
              }`}
              aria-current={currentTab === 'app' ? 'page' : undefined}
            >
              <Activity className="w-4 h-4 text-[#E3F26D]" />
              <span>Copilot App</span>
            </button>
            <button
              onClick={() => onSelectTab('evidence')}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all min-h-[44px] flex items-center gap-2 ${
                currentTab === 'evidence'
                  ? 'bg-[#17352B] text-white shadow-sm'
                  : 'text-[#5B6B63] hover:text-[#14201B]'
              }`}
              aria-current={currentTab === 'evidence' ? 'page' : undefined}
            >
              <BarChart3 className="w-4 h-4 text-[#F26B3A]" />
              <span>Evidence (N=1000)</span>
            </button>
          </div>

          {/* Local Status Indicator */}
          <div className="hidden lg:flex items-center gap-2 pl-3 border-l border-[#14201B]/10 text-xs font-medium text-[#17352B]">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#1F7A4D] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#1F7A4D]"></span>
            </span>
            <span>Local Loop 50Hz</span>
          </div>
        </nav>
      </div>
    </header>
  )
}
