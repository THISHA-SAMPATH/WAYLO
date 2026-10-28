import React, { useState } from 'react'
import { Mic, MicOff, Send, ShieldCheck, Cpu, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react'
import { api } from '../api/client'
import type { VoiceCommandResponse } from '../types'

export const VoiceSection: React.FC = () => {
  const [utterance, setUtterance] = useState<string>('Give me more room on the door')
  const [isListening, setIsListening] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<VoiceCommandResponse | null>(null)

  const presetUtterances = [
    'Give me more room on the door',
    'Slow down through narrow doors',
    'Normal speed',
    'Caregiver override mode',
  ]

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || utterance
    if (!text.trim()) return

    setLoading(true)
    setError(null)
    try {
      const data = await api.sendVoiceCommand(text)
      setResponse(data)
    } catch (err: any) {
      setError(err?.message || 'Voice command compilation failed')
    } finally {
      setLoading(false)
    }
  }

  // Optional Web Speech API support
  const toggleSpeechRecognition = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      setError('Speech recognition is not supported in this browser. Please use the text input.')
      return
    }

    if (isListening) {
      setIsListening(false)
      return
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = 'en-US'

      recognition.onstart = () => {
        setIsListening(true)
        setError(null)
      }

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript
        setUtterance(transcript)
        setIsListening(false)
        handleSend(transcript)
      }

      recognition.onerror = (e: any) => {
        setIsListening(false)
        setError(`Speech recognition notice: ${e.error || 'Check microphone permission'}`)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognition.start()
    } catch (e: any) {
      setIsListening(false)
      setError('Unable to activate speech recognition. Please type your command.')
    }
  }

  const isFallback =
    response?.source === 'offline_deterministic_fallback' ||
    response?.source === 'offline-safety-rules' ||
    !response?.source.includes('nemotron')

  return (
    <section id="voice" className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="rounded-3xl bg-white border border-[#14201B]/10 p-8 sm:p-12 shadow-soft-lg space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-[#14201B]/10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#17352B]/5 text-xs font-semibold text-[#17352B] mb-2">
              <Sparkles className="w-3.5 h-3.5 text-[#E3F26D]" />
              <span>Voice Adaptation Interface</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#14201B]">
              Natural Voice <span className="marker-highlight">Adaptation</span>
            </h2>
            <p className="text-base text-[#5B6B63] mt-1 max-w-2xl">
              Voice adapts parameters safely outside the 50 Hz control loop. Every voice parameter is bounded by strict physical safety clamps.
            </p>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#1F7A4D]/10 text-[#1F7A4D] border border-[#1F7A4D]/20">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Approved by safety layer</span>
            </span>

            {response && (
              <span
                id="voice-source-badge"
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                  isFallback
                    ? 'bg-amber-50 text-amber-900 border-amber-300'
                    : 'bg-emerald-50 text-emerald-900 border-emerald-300'
                }`}
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>
                  {isFallback
                    ? 'Fallback (offline)'
                    : `Nebius Nemotron (${response.model})`}
                </span>
              </span>
            )}
          </div>
        </div>

        {/* Mic & Input Control */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Big Mic Button (Left 3 cols) */}
          <div className="lg:col-span-3 flex flex-col items-center justify-center p-6 bg-[#F4F2EC] rounded-2xl border border-[#14201B]/10 text-center">
            <button
              onClick={toggleSpeechRecognition}
              aria-label={isListening ? 'Stop listening' : 'Start listening to voice command'}
              className={`w-24 h-24 rounded-full flex items-center justify-center transition-all shadow-md min-h-[96px] min-w-[96px] ${
                isListening
                  ? 'bg-[#C2410C] text-white animate-pulse ring-8 ring-[#C2410C]/20'
                  : 'bg-[#17352B] text-white hover:bg-[#1f473a]'
              }`}
            >
              {isListening ? <MicOff className="w-10 h-10" /> : <Mic className="w-10 h-10 text-[#E3F26D]" />}
            </button>
            <p className="mt-3 text-xs font-semibold text-[#14201B]">
              {isListening ? 'Listening now...' : 'Click to Speak'}
            </p>
            <p className="text-[11px] text-[#5B6B63] mt-0.5">or type your command</p>
          </div>

          {/* Text Input & Quick Presets (Right 9 cols) */}
          <div className="lg:col-span-9 space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                id="input-voice-utterance"
                value={utterance}
                onChange={(e) => setUtterance(e.target.value)}
                placeholder="e.g., 'Give me more room on the door' or 'Slow down'"
                aria-label="Voice command text input"
                className="flex-1 px-5 py-4 rounded-2xl border border-[#14201B]/15 bg-white text-[#14201B] placeholder:text-[#5B6B63]/60 focus:outline-none focus:ring-2 focus:ring-[#17352B] text-base min-h-[52px]"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSend()
                }}
              />
              <button
                onClick={() => handleSend()}
                disabled={loading || !utterance.trim()}
                id="btn-send-voice"
                aria-label="Send voice command"
                className="px-6 py-4 rounded-2xl bg-[#17352B] text-white font-semibold hover:bg-[#1f473a] transition disabled:opacity-50 min-h-[52px] flex items-center gap-2 shrink-0"
              >
                {loading ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                ) : (
                  <>
                    <span>Compile</span>
                    <Send className="w-4 h-4 text-[#E3F26D]" />
                  </>
                )}
              </button>
            </div>

            {/* Quick Test Presets */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-[#5B6B63] font-medium mr-1">Quick presets:</span>
              {presetUtterances.map((preset, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setUtterance(preset)
                    handleSend(preset)
                  }}
                  className="px-3 py-1.5 rounded-xl text-xs bg-[#F4F2EC] hover:bg-[#E3F26D]/30 border border-[#14201B]/10 text-[#14201B] font-medium transition min-h-[36px]"
                >
                  "{preset}"
                </button>
              ))}
            </div>

            {error && (
              <p className="text-xs text-red-600 bg-red-50 p-3 rounded-xl border border-red-200 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </p>
            )}
          </div>
        </div>

        {/* Result Chips & Explanation */}
        {response && (
          <div className="p-6 rounded-2xl bg-[#F4F2EC] border border-[#14201B]/10 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#5B6B63]">
                Compiled Safety Clamps
              </span>
              <span className="text-xs font-mono text-[#5B6B63]">
                Source: {response.source}
              </span>
            </div>

            {/* Plain Language Parameter Chips */}
            <div className="flex flex-wrap gap-3">
              <div className="px-4 py-2.5 rounded-xl bg-white border border-[#14201B]/10 shadow-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#1F7A4D]" />
                <span className="text-sm font-semibold text-[#14201B]">
                  Speed cap: {response.speed_cap_mps.toFixed(2)} m/s
                </span>
              </div>
              <div className="px-4 py-2.5 rounded-xl bg-white border border-[#14201B]/10 shadow-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#1F7A4D]" />
                <span className="text-sm font-semibold text-[#14201B]">
                  Extra margin: +{(response.clearance_margin_m * 100).toFixed(0)} cm
                </span>
              </div>
              <div className="px-4 py-2.5 rounded-xl bg-white border border-[#14201B]/10 shadow-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#1F7A4D]" />
                <span className="text-sm font-semibold text-[#14201B]">
                  Door mode: {response.door_mode}
                </span>
              </div>
            </div>

            <div className="text-xs sm:text-sm text-[#5B6B63] bg-white p-3.5 rounded-xl border border-[#14201B]/5">
              <span className="font-semibold text-[#14201B]">Intent Interpretation: </span>
              <span>{response.intent_summary || 'Command processed and checked against kinematic limits.'}</span>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
