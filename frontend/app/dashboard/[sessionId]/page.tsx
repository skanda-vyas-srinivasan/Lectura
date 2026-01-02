'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { API_URL } from '@/lib/config'

interface ProcessingStatus {
  phase: string
  progress: number
  message: string
  complete: boolean
  total_slides?: number
}

export default function Dashboard() {
  const router = useRouter()
  const params = useParams()
  const sessionId = params.sessionId as string

  const [status, setStatus] = useState<ProcessingStatus>({
    phase: 'starting',
    progress: 0,
    message: 'Getting things ready...',
    complete: false
  })
  const [error, setError] = useState<string | null>(null)
  const [isCanceling, setIsCanceling] = useState(false)

  useEffect(() => {
    let intervalId: NodeJS.Timeout

    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/session/${sessionId}/status`)

        if (!response.ok) {
          throw new Error('Failed to fetch status')
        }

        const data = await response.json()
        setStatus(data)

        // If processing is complete, redirect to viewer
        if (data.complete) {
          clearInterval(intervalId)
          setTimeout(() => {
            router.push(`/lecture/${sessionId}`)
          }, 1500)
        }
        if (data.phase === 'canceled') {
          clearInterval(intervalId)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch status')
        clearInterval(intervalId)
      }
    }

    // Start polling
    checkStatus()
    intervalId = setInterval(checkStatus, 2000)

    return () => clearInterval(intervalId)
  }, [sessionId, router])

  const getPhaseLabel = (phase: string) => {
    const labels: Record<string, string> = {
      converting: 'Converting PPTX',
      parsing: 'Reading slides',
      extracting_images: 'Rendering slides',
      building_context: 'Understanding the lecture',
      generating_narrations: 'Writing narration',
      generating_audio: 'Recording audio',
      creating_viewer: 'Finalizing lecture',
      canceled: 'Canceled',
      complete: 'Complete!'
    }
    return labels[phase] || phase
  }

  const phases = [
    'converting',
    'parsing',
    'extracting_images',
    'building_context',
    'generating_narrations',
    'generating_audio',
    'creating_viewer'
  ]

  const canCancel = !status.complete && status.phase !== 'canceled' && status.phase !== 'error'

  const cancelProcessing = async () => {
    if (isCanceling) return
    setIsCanceling(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/session/${sessionId}/cancel`, {
        method: 'POST',
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to cancel')
      }
      const data = await response.json()
      if (data?.status) {
        setStatus(data.status)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel')
    } finally {
      setIsCanceling(false)
    }
  }

  const currentPhaseIndex = phases.indexOf(status.phase)

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-10 bg-sky-100 page-fade-in">
      <div className="max-w-3xl w-full">
        <div className="text-center mb-10">
          <h1 className="text-3xl md:text-4xl font-semibold text-slate-900">
            Processing Your Lecture
          </h1>
          <p className="text-base text-slate-600 mt-3">
            This can take a few minutes for large decks.
          </p>
        </div>

        <div className="bg-white rounded-2xl p-8 border border-slate-200 text-slate-900 shadow-sm">
          {/* Current phase text */}
          <div className="mb-8 text-center">
            <p className="text-sm font-semibold text-slate-900">
              {getPhaseLabel(status.phase)}
            </p>
            {status.total_slides && (
              <p className="text-xs text-slate-500 mt-2">
                Total slides: {status.total_slides}
              </p>
            )}
            {canCancel && (
              <div className="mt-4 flex justify-center">
                <button
                  onClick={cancelProcessing}
                  disabled={isCanceling}
                  className="px-4 py-2 text-xs font-semibold text-red-700 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isCanceling ? 'Canceling…' : 'Cancel Processing'}
                </button>
              </div>
            )}
          </div>

          {/* Progress bar */}
          <div className="mb-8">
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-sky-500 h-full transition-all duration-500 ease-out"
                style={{ width: `${status.progress}%` }}
              ></div>
            </div>
            <p className="text-center text-xs text-slate-500 mt-2">
              {Math.round(status.progress)}% complete
            </p>
          </div>

          {/* Phase checklist */}
          <div className="space-y-2">
            {phases.map((phase, index) => {
              const isComplete = index < currentPhaseIndex || status.complete
              const isCurrent = index === currentPhaseIndex && !status.complete

              return (
                <div
                  key={phase}
                  className={`flex items-center justify-between px-4 py-2 rounded-lg transition-colors ${
                    isCurrent ? 'bg-slate-50 border border-slate-200' : 'bg-slate-50'
                  }`}
                >
                  <span className={`text-sm ${isComplete ? 'text-emerald-600' : isCurrent ? 'text-slate-900 font-semibold' : 'text-slate-600'}`}>
                    {getPhaseLabel(phase)}
                  </span>
                  {isComplete ? (
                    <span className="text-xs text-emerald-600">Done</span>
                  ) : isCurrent ? (
                    <span className="text-xs text-slate-500">In progress</span>
                  ) : (
                    <span className="text-xs text-slate-400">Queued</span>
                  )}
                </div>
              )
            })}
          </div>

          {status.phase === 'error' && (
            <div className="mt-6 bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg">
              <p className="font-semibold">Processing failed</p>
              <p className="text-sm mt-1">{status.message}</p>
              <p className="text-xs text-red-600 mt-2">Try re-uploading or reducing slide count.</p>
            </div>
          )}

          {status.complete && (
            <div className="mt-8 text-center">
              <div className="inline-flex items-center space-x-2 text-emerald-600">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-xl font-semibold">Processing Complete!</span>
              </div>
              <p className="text-slate-500 mt-2">Redirecting to viewer...</p>
            </div>
          )}

          {status.phase === 'canceled' && (
            <div className="mt-6 text-center">
              <div className="inline-flex items-center space-x-2 text-slate-600">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span className="text-base font-semibold">Processing canceled</span>
              </div>
              <p className="text-slate-500 mt-2">You can upload a new file whenever you're ready.</p>
              <div className="mt-4">
                <button
                  onClick={() => router.push('/')}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 border border-slate-200 rounded-lg hover:bg-slate-50"
                >
                  Back to Upload
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-6 bg-red-50 border border-red-200 text-red-600 px-6 py-4 rounded-lg">
              <p className="font-semibold">Error:</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
