'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { API_URL } from '@/lib/config'

export default function Home() {
  const router = useRouter()
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [enableVision, setEnableVision] = useState(false)
  const [ttsProvider, setTtsProvider] = useState<'edge' | 'polly'>('polly')
  const [pollyVoice, setPollyVoice] = useState<string>('Matthew')

  // TTS Test state
  const [showTtsTest, setShowTtsTest] = useState(false)
  const [ttsTestText, setTtsTestText] = useState('Hello, this is a test of the text to speech system.')
  const [ttsTestLoading, setTtsTestLoading] = useState(false)
  const [ttsTestError, setTtsTestError] = useState<string | null>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const uploadFile = async (file: File) => {
    setUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_URL}/api/v1/upload?enable_vision=${enableVision}&tts_provider=${ttsProvider}&polly_voice=${pollyVoice}`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const data = await response.json()
      router.push(`/dashboard/${data.session_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      if (file.type === 'application/pdf' ||
          file.type === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
        uploadFile(file)
      } else {
        setError('Please upload a PDF or PPTX file')
      }
    }
  }, [uploadFile])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadFile(file)
    }
  }

  const testTts = async () => {
    setTtsTestLoading(true)
    setTtsTestError(null)

    try {
      const response = await fetch(
        `${API_URL}/api/v1/test-tts?text=${encodeURIComponent(ttsTestText)}&provider=${ttsProvider}`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'TTS test failed')
      }

      // Get the audio blob
      const audioBlob = await response.blob()
      const audioUrl = URL.createObjectURL(audioBlob)

      // Play the audio
      const audio = new Audio(audioUrl)
      audio.play()

      setTtsTestLoading(false)
    } catch (err) {
      setTtsTestError(err instanceof Error ? err.message : 'TTS test failed')
      setTtsTestLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-sky-100">
      {/* Animated background */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-sky-100 via-sky-200 to-blue-200"></div>
        <div className="absolute top-0 -left-4 w-72 h-72 bg-sky-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob"></div>
        <div className="absolute top-0 -right-4 w-72 h-72 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-72 h-72 bg-cyan-300 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob animation-delay-4000"></div>
      </div>

      {/* Grid overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a12_1px,transparent_1px),linear-gradient(to_bottom,#0f172a12_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>

      <main className="relative min-h-screen flex items-center justify-center p-8">
        <div className="max-w-5xl w-full">
          {/* Header */}
          <div className="text-center mb-16 space-y-6">
            <h1 className="text-7xl md:text-8xl font-black mb-6 tracking-tight">
              <span className="bg-gradient-to-r from-blue-300 via-sky-300 to-cyan-200 text-transparent bg-clip-text animate-gradient">
                AI Lecturer
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-slate-700 max-w-2xl mx-auto">
              Transform your slides into <span className="text-slate-900 font-semibold">clear, narrated lectures</span> with AI
            </p>

            <button
              onClick={() => router.push('/presentations')}
              className="inline-flex items-center space-x-2 text-slate-700 hover:text-slate-900 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span>View Your Presentations</span>
            </button>
          </div>

          {/* Upload area */}
          <div className="space-y-6">
            {/* Settings toggles */}
            <div className="flex justify-center gap-4">
              <label className="group relative cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableVision}
                  onChange={(e) => setEnableVision(e.target.checked)}
                  className="peer sr-only"
                />
                <div className="flex items-center space-x-4 bg-white/70 backdrop-blur-xl border border-slate-200 rounded-2xl px-6 py-4 transition-all peer-checked:border-blue-400 peer-checked:bg-blue-100 hover:bg-white">
                  <div className="w-12 h-6 bg-slate-300 rounded-full relative transition-colors peer-checked:bg-blue-500">
                    <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${enableVision ? 'translate-x-6' : ''}`}></div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-slate-900 flex items-center space-x-2">
                      <span>Vision Analysis</span>
                      {enableVision && <span className="text-xs bg-blue-500/20 text-blue-700 px-2 py-0.5 rounded-full">ON</span>}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5">
                      Analyze diagrams, tables & charts
                    </div>
                  </div>
                </div>
              </label>

              {/* TTS Provider selector */}
              <div className="bg-white/70 backdrop-blur-xl border border-slate-200 rounded-2xl px-6 py-4">
                <label className="block text-sm font-semibold text-slate-900 mb-3">
                  🎤 Voice Provider
                </label>
                <select
                  value={ttsProvider}
                  onChange={(e) => setTtsProvider(e.target.value as 'edge' | 'polly')}
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/50 transition-all"
                >
                  <option value="polly" className="bg-white">🎤 AWS Polly (Neural) - Better Quality</option>
                  <option value="edge" className="bg-white">🔊 Edge TTS - Fast & Free</option>
                </select>

                {/* Polly Voice Selector */}
                {ttsProvider === 'polly' && (
                  <div className="mt-3">
                    <label className="block text-xs font-semibold text-slate-700 mb-2">
                      Voice
                    </label>
                    <select
                      value={pollyVoice}
                      onChange={(e) => setPollyVoice(e.target.value)}
                      className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/50 transition-all"
                    >
                      <option value="Matthew" className="bg-white">Matthew (Male, US)</option>
                      <option value="Joanna" className="bg-white">Joanna (Female, US)</option>
                      <option value="Salli" className="bg-white">Salli (Female, US)</option>
                      <option value="Joey" className="bg-white">Joey (Male, US)</option>
                      <option value="Justin" className="bg-white">Justin (Male, US)</option>
                      <option value="Kevin" className="bg-white">Kevin (Male, US)</option>
                      <option value="Kendra" className="bg-white">Kendra (Female, US)</option>
                      <option value="Ruth" className="bg-white">Ruth (Female, US)</option>
                      <option value="Stephen" className="bg-white">Stephen (Male, US)</option>
                    </select>
                  </div>
                )}

                <div className="text-xs text-slate-600 mt-2">
                  {ttsProvider === 'polly' ? 'High-quality neural voices (requires AWS setup)' : 'Free voice synthesis - no setup required'}
                </div>
              </div>
            </div>

            {/* Upload zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative group`}
            >
              <div className={`absolute inset-0 bg-gradient-to-r from-sky-400 via-blue-400 to-cyan-400 rounded-3xl blur-xl opacity-0 group-hover:opacity-30 transition-opacity ${isDragging ? 'opacity-40' : ''}`}></div>

              <div className={`relative bg-slate-900/85 backdrop-blur-xl border-2 border-dashed rounded-3xl p-20 text-center transition-all ${
                isDragging
                  ? 'border-sky-300 bg-sky-500/15 scale-105'
                  : 'border-white/20 hover:border-white/40'
              } ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>

                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  accept=".pdf,.pptx"
                  onChange={handleFileSelect}
                  disabled={uploading}
                />

                {uploading ? (
                  <div className="flex flex-col items-center space-y-6">
                    <div className="relative w-20 h-20">
                      <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full"></div>
                      <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
                    </div>
                    <div className="space-y-2">
                      <p className="text-2xl font-bold text-white">Uploading...</p>
                      <p className="text-sm text-slate-300">Preparing your lecture</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-8">
                    <div className="relative inline-block">
                      <div className="absolute inset-0 bg-gradient-to-r from-sky-400 to-blue-500 rounded-2xl blur-2xl opacity-50"></div>
                      <div className="relative bg-gradient-to-br from-sky-500/20 to-blue-500/20 p-8 rounded-2xl">
                        <svg className="w-20 h-20 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <p className="text-3xl font-bold text-white">
                        {isDragging ? 'Drop it here!' : 'Drop your lecture deck'}
                      </p>
                      <p className="text-slate-400">or</p>
                      <label
                        htmlFor="file-upload"
                        className="inline-flex items-center space-x-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white font-bold py-4 px-10 rounded-xl transition-all transform hover:scale-105 cursor-pointer"
                      >
                        <span>Browse Files</span>
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </label>
                      <p className="text-sm text-slate-400 font-mono">
                        PDF • PPTX • Max 100MB
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="bg-red-500/10 backdrop-blur-xl border border-red-500/20 rounded-2xl px-6 py-4">
                <div className="flex items-start space-x-3">
                  <svg className="w-5 h-5 text-red-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <p className="text-sm font-semibold text-red-300">Upload Failed</p>
                    <p className="text-sm text-red-400/80 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* TTS Test Section */}
            <div className="mt-8">
              <button
                onClick={() => setShowTtsTest(!showTtsTest)}
                className="w-full text-center text-sm text-slate-600 hover:text-slate-700 transition-colors"
              >
                {showTtsTest ? '▼' : '▶'} TTS Quick Test (Debug)
              </button>

              {showTtsTest && (
                <div className="mt-4 bg-slate-900/85 backdrop-blur-xl border border-white/10 rounded-2xl p-6 space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm text-slate-300">Test Text:</label>
                    <textarea
                      value={ttsTestText}
                      onChange={(e) => setTtsTestText(e.target.value)}
                      className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white placeholder-slate-400 focus:outline-none focus:border-sky-400 transition-colors"
                      rows={3}
                      placeholder="Enter text to test TTS..."
                    />
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={testTts}
                      disabled={ttsTestLoading || !ttsTestText}
                      className="flex-1 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 px-6 rounded-xl transition-all"
                    >
                      {ttsTestLoading ? (
                        <span className="flex items-center justify-center space-x-2">
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                          <span>Testing...</span>
                        </span>
                      ) : (
                        `Test Edge TTS`
                      )}
                    </button>
                  </div>

                  {ttsTestError && (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                      <p className="text-sm text-red-300 font-mono">{ttsTestError}</p>
                    </div>
                  )}

                  <p className="text-xs text-slate-400 text-center">
                    This will play audio directly in your browser. Make sure your volume is on!
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>
      </main>

      <style jsx>{`
        @keyframes blob {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -50px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
        @keyframes gradient {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 3s ease infinite;
        }
      `}</style>
    </div>
  )
}
