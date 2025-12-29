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
    message: 'Initializing...',
    complete: false
  })
  const [error, setError] = useState<string | null>(null)

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
      parsing: 'Parsing PDF',
      extracting_images: 'Extracting Slide Images',
      building_context: 'Building Global Context',
      generating_narrations: 'Generating Narrations',
      generating_audio: 'Generating Audio Files',
      creating_viewer: 'Creating Viewer',
      complete: 'Complete!'
    }
    return labels[phase] || phase
  }

  const phases = [
    'parsing',
    'extracting_images',
    'building_context',
    'generating_narrations',
    'generating_audio',
    'creating_viewer'
  ]

  const currentPhaseIndex = phases.indexOf(status.phase)

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
            Processing Your Lecture
          </h1>
          <p className="text-xl text-gray-300">
            This may take a few minutes...
          </p>
        </div>

        <div className="bg-slate-800/50 rounded-2xl p-8 border border-gray-700">
          {/* Current phase indicator */}
          <div className="mb-8 text-center">
            <div className="inline-flex items-center space-x-3 bg-blue-950/50 px-6 py-3 rounded-full border border-blue-500">
              {!status.complete && (
                <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse"></div>
              )}
              <span className="text-lg font-semibold text-blue-300">
                {getPhaseLabel(status.phase)}
              </span>
            </div>
            <p className="text-gray-400 mt-4">{status.message}</p>
            {status.total_slides && (
              <p className="text-sm text-gray-500 mt-2">
                Total slides: {status.total_slides}
              </p>
            )}
          </div>

          {/* Progress bar */}
          <div className="mb-8">
            <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-full transition-all duration-500 ease-out"
                style={{ width: `${status.progress}%` }}
              ></div>
            </div>
            <p className="text-center text-sm text-gray-400 mt-2">
              {Math.round(status.progress)}% complete
            </p>
          </div>

          {/* Phase checklist */}
          <div className="space-y-3">
            {phases.map((phase, index) => {
              const isComplete = index < currentPhaseIndex || status.complete
              const isCurrent = index === currentPhaseIndex && !status.complete

              return (
                <div
                  key={phase}
                  className={`flex items-center space-x-3 p-3 rounded-lg transition-all ${
                    isCurrent ? 'bg-blue-950/30 border border-blue-500/30' : 'bg-slate-700/30'
                  }`}
                >
                  {isComplete ? (
                    <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isCurrent ? (
                    <div className="w-6 h-6 border-3 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <div className="w-6 h-6 border-2 border-gray-600 rounded-full"></div>
                  )}
                  <span className={`${isComplete ? 'text-green-300' : isCurrent ? 'text-blue-300 font-semibold' : 'text-gray-500'}`}>
                    {getPhaseLabel(phase)}
                  </span>
                </div>
              )
            })}
          </div>

          {status.complete && (
            <div className="mt-8 text-center">
              <div className="inline-flex items-center space-x-2 text-green-400">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-xl font-semibold">Processing Complete!</span>
              </div>
              <p className="text-gray-400 mt-2">Redirecting to viewer...</p>
            </div>
          )}

          {error && (
            <div className="mt-6 bg-red-900/50 border border-red-500 text-red-200 px-6 py-4 rounded-lg">
              <p className="font-semibold">Error:</p>
              <p>{error}</p>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
