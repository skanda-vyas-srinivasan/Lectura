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
  const [ttsProvider, setTtsProvider] = useState<'edge' | 'polly'>('edge')
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
    <div className="min-h-screen bg-sky-100 text-slate-900 page-fade-in">

      <main className="relative min-h-screen flex flex-col items-center justify-center p-10">
        <div className="max-w-6xl w-full">
          <div className="grid gap-10 md:grid-cols-2 md:items-start">
            {/* Left column */}
              <div className="space-y-7">
                <div className="space-y-3">
                  <h1 className="text-5xl md:text-6xl font-semibold tracking-tight text-slate-900">
                    Lectora
                  </h1>

                  <button
                    onClick={() => router.push('/purpose')}
                    className="inline-flex items-center space-x-2 text-slate-600 hover:text-slate-900 transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Why I Built This</span>
                  </button>

                  <p className="text-lg md:text-xl text-slate-700 max-w-xl leading-relaxed">
                    Turn slide decks into clear, narrated lectures.
                  </p>

                <button
                  onClick={() => router.push('/presentations')}
                  className="inline-flex items-center space-x-2 text-slate-600 hover:text-slate-900 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <span>View Your Presentations</span>
                </button>

              </div>

              {/* Settings */}
              <div className="bg-white/80 border border-slate-200 rounded-2xl divide-y divide-slate-100">
                <div className="px-5 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="text-sm font-semibold text-slate-900">Vision Analysis</div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <span className="text-xs text-slate-500 w-8 text-right">{enableVision ? 'On' : 'Off'}</span>
                    <input
                      type="checkbox"
                      checked={enableVision}
                      onChange={(e) => setEnableVision(e.target.checked)}
                      className="peer sr-only"
                    />
                    <div className="w-10 h-5 bg-slate-200 rounded-full relative transition-colors peer-checked:bg-sky-500">
                      <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${enableVision ? 'translate-x-5' : ''}`}></div>
                    </div>
                  </label>
                </div>

                <div className="px-5 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="text-sm font-semibold text-slate-900">Voice Provider</div>
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-3">
                    <select
                      value={ttsProvider}
                      onChange={(e) => setTtsProvider(e.target.value as 'edge' | 'polly')}
                      className="w-full md:w-52 bg-white border border-slate-200 rounded-lg px-4 py-2 text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/40"
                    >
                      <option value="polly" className="bg-white">AWS Polly (Neural)</option>
                      <option value="edge" className="bg-white">Edge TTS</option>
                    </select>

                    <select
                      value={pollyVoice}
                      onChange={(e) => setPollyVoice(e.target.value)}
                      disabled={ttsProvider !== 'polly'}
                      className="w-full md:w-52 bg-white border border-slate-200 rounded-lg px-4 py-2 text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/40 disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed"
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
                </div>
              </div>
            </div>

            {/* Right column */}
            <div className="relative md:pt-2">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className="relative"
              >
                <div className={`bg-white border-2 border-dashed rounded-2xl p-10 text-center transition-colors min-h-[320px] flex items-center justify-center ${
                  isDragging
                    ? 'border-sky-400 bg-sky-50'
                    : 'border-slate-200 hover:border-slate-300'
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
                      <div className="flex flex-col items-center space-y-5">
                        <div className="relative w-16 h-16">
                          <div className="absolute inset-0 border-4 border-sky-200 rounded-full"></div>
                          <div className="absolute inset-0 border-4 border-transparent border-t-sky-500 rounded-full animate-spin"></div>
                        </div>
                        <div className="space-y-2">
                          <p className="text-xl font-semibold text-slate-900">Uploading...</p>
                          <p className="text-sm text-slate-600">Preparing your lecture</p>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-6">
                        <div className="space-y-4">
                          <p className="text-xl font-semibold text-slate-900">
                            {isDragging ? 'Drop it here!' : 'Drop your lecture deck'}
                          </p>
                          <p className="text-slate-500">or</p>
                          <label
                            htmlFor="file-upload"
                            className="inline-flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold py-2.5 px-6 rounded-lg transition-colors cursor-pointer"
                          >
                            <span>Browse Files</span>
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                          </label>
                          <p className="text-sm text-slate-500 font-mono">
                            PDF • PPTX • Max 100MB
                          </p>
                        </div>
                      </div>
                    )}
                </div>
              </div>

              {error && (
                <div className="mt-6 bg-red-50 border border-red-200 rounded-2xl px-6 py-4">
                  <div className="flex items-start space-x-3">
                    <svg className="w-5 h-5 text-red-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <p className="text-sm font-semibold text-red-700">Upload Failed</p>
                      <p className="text-sm text-red-600 mt-1">{error}</p>
                    </div>
                  </div>
                </div>
              )}

            </div>
          </div>

        </div>
        <div className="mt-10 text-xs text-slate-500">
          Update log: added PPTX support
        </div>
      </main>

    </div>
  )
}
