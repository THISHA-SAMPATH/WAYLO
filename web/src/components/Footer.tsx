import React from 'react'
import { ExternalLink, Code } from 'lucide-react'

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-[#14201B] text-white/70 py-16 border-t border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        {/* Top wordmarks & partners */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-10 border-b border-white/10">
          <div>
            <div className="flex items-center gap-3">
              <span className="font-extrabold text-2xl tracking-tight text-white">WAYLO</span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#E3F26D] text-[#17352B]">
                Physical AI Copilot
              </span>
            </div>
            <p className="text-xs text-white/60 mt-1">
              Shared-autonomy doorway assistant for power wheelchairs.
            </p>
          </div>

          {/* Partner Wordmarks (clean text/wordmarks, no trademarked logos) */}
          <div className="flex flex-wrap items-center gap-6 text-xs sm:text-sm font-medium text-white/80">
            <span className="text-white/40 uppercase tracking-wider text-[11px]">Built with</span>
            <span className="hover:text-white transition font-semibold">Nebius Token Factory</span>
            <span className="text-white/30">·</span>
            <span className="hover:text-white transition font-semibold">NVIDIA Nemotron</span>
            <span className="text-white/30">·</span>
            <span className="hover:text-white transition font-semibold">Tavily</span>
          </div>
        </div>

        {/* Bottom meta & links */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-white/50">
          <div className="flex items-center gap-4">
            <span>Released under the <strong className="text-white">MIT License</strong></span>
            <span>·</span>
            <span>Simulation Research Prototype</span>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="hover:text-white transition flex items-center gap-1.5"
            >
              <Code className="w-4 h-4" />
              <span>GitHub Repository</span>
            </a>
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="hover:text-white transition flex items-center gap-1.5"
            >
              <ExternalLink className="w-4 h-4" />
              <span>FastAPI OpenAPI Docs</span>
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
