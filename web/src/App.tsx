import React, { useState, useEffect } from 'react'
import { Navbar } from './components/Navbar'
import { Hero } from './components/Hero'
import { StatStrip } from './components/StatStrip'
import { LiveDemo } from './components/LiveDemo'
import { VoiceSection } from './components/VoiceSection'
import { CaregiverDashboard } from './components/CaregiverDashboard'
import { StandardsSection } from './components/StandardsSection'
import { EvidencePage } from './components/EvidencePage'
import { Footer } from './components/Footer'
import { api } from './api/client'
import type { MonteCarloSummaryResponse } from './types'

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'app' | 'evidence'>('app')
  const [summary, setSummary] = useState<MonteCarloSummaryResponse | null>(null)
  const [loadingSummary, setLoadingSummary] = useState<boolean>(true)
  const [summaryError, setSummaryError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSummary = async () => {
      setLoadingSummary(true)
      try {
        const data = await api.getMonteCarloSummary()
        setSummary(data)
      } catch (err: any) {
        setSummaryError(err?.message || 'Failed to load Monte Carlo summary')
      } finally {
        setLoadingSummary(false)
      }
    }
    fetchSummary()
  }, [])

  const scrollToSection = (id: string) => {
    if (currentTab !== 'app') {
      setCurrentTab('app')
      setTimeout(() => {
        const el = document.getElementById(id)
        if (el) el.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    } else {
      const el = document.getElementById(id)
      if (el) el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const handleApplyDoorWidth = (_widthM: number) => {
    scrollToSection('demo')
  }

  return (
    <div className="min-h-screen bg-[#F4F2EC] text-[#14201B] flex flex-col font-sans selection:bg-[#E3F26D] selection:text-[#17352B]">
      {/* Sticky Top Navigation */}
      <Navbar
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setCurrentTab(tab)
          window.scrollTo({ top: 0, behavior: 'smooth' })
        }}
        onScrollToSection={scrollToSection}
      />

      <main className="flex-1">
        {currentTab === 'app' ? (
          <>
            {/* Section 1: Hero */}
            <Hero
              onTryDemo={() => scrollToSection('demo')}
              onSeeEvidence={() => {
                setCurrentTab('evidence')
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
            />

            {/* Section 2: Empirical Stat Strip */}
            <StatStrip
              summary={summary}
              loading={loadingSummary}
              error={summaryError}
            />

            {/* Section 3: Interactive 3D Digital Twin Demo */}
            <LiveDemo />

            {/* Section 4: Voice Adaptation */}
            <VoiceSection />

            {/* Section 5: Caregiver Dashboard & Privacy Receipt */}
            <CaregiverDashboard />

            {/* Section 6: Accessibility Standards */}
            <StandardsSection onApplyDoorWidth={handleApplyDoorWidth} />
          </>
        ) : (
          /* Section 7: Full Evidence Page */
          <EvidencePage
            onBackToApp={() => {
              setCurrentTab('app')
              window.scrollTo({ top: 0, behavior: 'smooth' })
            }}
          />
        )}
      </main>

      {/* Section 8: Partner Wordmarks & Footer */}
      <Footer />
    </div>
  )
}

export default App
