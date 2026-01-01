'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { API_URL } from '@/lib/config'

interface Presentation {
  id: string
  filename: string
  created_at: string
  total_slides: number
  enable_vision: boolean
  tts_provider: string
}

export default function PresentationsPage() {
  const router = useRouter()
  const [presentations, setPresentations] = useState<Presentation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPresentations()
  }, [])

  const fetchPresentations = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/sessions`)
      if (!response.ok) throw new Error('Failed to fetch presentations')
      
      const data = await response.json()
      setPresentations(data.sessions)
      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load presentations')
      setLoading(false)
    }
  }

  const formatDate = (isoDate: string) => {
    const date = new Date(isoDate)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen bg-sky-100">
      {/* Background */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-sky-100 via-sky-200 to-blue-200"></div>
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a12_1px,transparent_1px),linear-gradient(to_bottom,#0f172a12_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>
      </div>

      {/* Content */}
      <div className="relative min-h-screen p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-12">
            <button
              onClick={() => router.push('/')}
              className="text-slate-700 hover:text-slate-900 mb-6 flex items-center space-x-2 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span>Back to Home</span>
            </button>

            <h1 className="text-5xl font-black mb-4">
              <span className="bg-gradient-to-r from-sky-600 via-blue-700 to-cyan-600 text-transparent bg-clip-text">
                Your Presentations
              </span>
            </h1>
            <p className="text-xl text-slate-700">
              All your generated lectures in one place
            </p>
          </div>

          {/* Loading state */}
          {loading && (
            <div className="flex items-center justify-center py-20">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
              </div>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="bg-red-500/10 backdrop-blur-xl border border-red-500/20 rounded-2xl px-6 py-4">
              <div className="flex items-start space-x-3">
                <svg className="w-5 h-5 text-red-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-sm font-semibold text-red-300">Error</p>
                  <p className="text-sm text-red-400/80 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Presentations grid */}
          {!loading && !error && (
            <>
              {presentations.length === 0 ? (
                <div className="text-center py-20">
                  <div className="inline-block bg-slate-900/85 backdrop-blur-xl border border-white/10 rounded-2xl p-12 text-white">
                    <svg className="w-20 h-20 text-gray-600 mx-auto mb-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-xl font-semibold text-slate-200 mb-2">No presentations yet</p>
                    <p className="text-slate-400 mb-6">Upload your first lecture to get started</p>
                    <button
                      onClick={() => router.push('/')}
                      className="inline-flex items-center space-x-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-600 hover:to-blue-700 text-white font-bold py-3 px-8 rounded-xl transition-all transform hover:scale-105"
                    >
                      <span>Upload Lecture</span>
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {presentations.map((presentation) => (
                    <div
                      key={presentation.id}
                      onClick={() => router.push(`/lecture/${presentation.id}`)}
                      className="group relative bg-slate-900/85 backdrop-blur-xl border border-white/10 rounded-2xl p-6 hover:border-sky-300/60 hover:bg-sky-500/10 transition-all cursor-pointer transform hover:scale-105 text-white"
                    >
                      {/* Glow effect on hover */}
                      <div className="absolute inset-0 bg-gradient-to-r from-sky-400 via-blue-500 to-cyan-400 rounded-2xl blur-xl opacity-0 group-hover:opacity-20 transition-opacity"></div>

                      <div className="relative">
                        {/* Icon */}
                        <div className="w-12 h-12 bg-gradient-to-br from-sky-500/20 to-blue-500/20 rounded-xl flex items-center justify-center mb-4">
                          <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>

                        {/* Filename */}
                        <h3 className="text-lg font-bold text-white mb-2 truncate">
                          {presentation.filename}
                        </h3>

                        {/* Metadata */}
                        <div className="space-y-2 mb-4">
                          <div className="flex items-center space-x-2 text-sm text-slate-300">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>{formatDate(presentation.created_at)}</span>
                          </div>

                          <div className="flex items-center space-x-2 text-sm text-slate-300">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            <span>{presentation.total_slides} slides</span>
                          </div>
                        </div>

                        {/* Tags */}
                        <div className="flex flex-wrap gap-2">
                          {presentation.enable_vision && (
                            <span className="text-xs bg-sky-500/20 text-sky-200 px-2 py-1 rounded-full">
                              Vision
                            </span>
                          )}
                          <span className="text-xs bg-blue-500/20 text-blue-200 px-2 py-1 rounded-full">
                            {presentation.tts_provider === 'google' ? 'Google TTS' : 'Edge TTS'}
                          </span>
                        </div>

                        {/* Play icon */}
                        <div className="absolute top-0 right-0 w-10 h-10 bg-gradient-to-br from-sky-500 to-blue-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <svg className="w-5 h-5 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
