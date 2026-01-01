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
      {/* Content */}
      <div className="min-h-screen p-8">
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

            <h1 className="text-4xl md:text-5xl font-semibold text-slate-900 mb-4">
              Your Presentations
            </h1>
            <p className="text-lg text-slate-600">
              All your generated lectures in one place.
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
            <div className="bg-red-50 border border-red-200 rounded-2xl px-6 py-4">
              <div className="flex items-start space-x-3">
                <svg className="w-5 h-5 text-red-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="text-sm font-semibold text-red-700">Error</p>
                  <p className="text-sm text-red-600 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Presentations grid */}
          {!loading && !error && (
            <>
              {presentations.length === 0 ? (
                <div className="text-center py-20">
                  <div className="inline-block bg-white border border-slate-200 rounded-2xl p-12 text-slate-900">
                    <svg className="w-16 h-16 text-slate-300 mx-auto mb-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-xl font-semibold text-slate-900 mb-2">No presentations yet</p>
                    <p className="text-slate-600 mb-6">Upload your first lecture to get started.</p>
                    <button
                      onClick={() => router.push('/')}
                      className="inline-flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-8 rounded-lg transition-colors"
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
                      className="group relative bg-white border border-slate-200 rounded-2xl p-6 hover:border-slate-300 transition-colors cursor-pointer"
                    >
                      <div className="relative">
                        {/* Icon */}
                        <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center mb-4">
                          <svg className="w-6 h-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>

                        {/* Filename */}
                        <h3 className="text-lg font-semibold text-slate-900 mb-2 truncate">
                          {presentation.filename}
                        </h3>

                        {/* Metadata */}
                        <div className="space-y-2 mb-4">
                          <div className="flex items-center space-x-2 text-sm text-slate-600">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>{formatDate(presentation.created_at)}</span>
                          </div>

                          <div className="flex items-center space-x-2 text-sm text-slate-600">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            <span>{presentation.total_slides} slides</span>
                          </div>
                        </div>

                        {/* Tags */}
                        <div className="flex flex-wrap gap-2">
                          {presentation.enable_vision && (
                            <span className="text-xs bg-sky-100 text-sky-700 px-2 py-1 rounded-full">
                              Vision
                            </span>
                          )}
                          <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full">
                            {presentation.tts_provider === 'google' ? 'Google TTS' : 'Edge TTS'}
                          </span>
                        </div>

                        {/* Play icon */}
                        <div className="absolute top-0 right-0 w-9 h-9 bg-slate-900 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <svg className="w-4 h-4 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
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
