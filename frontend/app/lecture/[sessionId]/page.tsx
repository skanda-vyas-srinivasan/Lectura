'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams } from 'next/navigation'
import { API_URL } from '@/lib/config'

interface WordTiming {
  word: string
  start_time: number
}

interface LectureData {
  pdf_name: string
  total_slides: number
  narrations: Record<string, string>
  slide_titles: string[]
  word_timings: Record<string, WordTiming[]>
}

export default function LectureViewer() {
  const params = useParams()
  const sessionId = params.sessionId as string

  const [lectureData, setLectureData] = useState<LectureData | null>(null)
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [showTranscript, setShowTranscript] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [currentSubtitle, setCurrentSubtitle] = useState('')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioError, setAudioError] = useState<string | null>(null)

  const audioRef = useRef<HTMLAudioElement>(null)
  const prefetchAudioRef = useRef<HTMLAudioElement | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const hideControlsTimeout = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/session/${sessionId}/lecture`)
        const data = await response.json()
        setLectureData(data)
      } catch (err) {
        console.error('Failed to load lecture data:', err)
      }
    }

    fetchData()
  }, [sessionId])

  useEffect(() => {
    if (audioRef.current && lectureData) {
      setAudioLoading(true)
      setAudioError(null)
      audioRef.current.src = `${API_URL}/api/v1/session/${sessionId}/audio/${currentSlide}`
      audioRef.current.load()
      if (isPlaying) {
        audioRef.current.play().catch(() => {
          setIsPlaying(false)
        })
      }
    }
  }, [currentSlide, sessionId, lectureData])

  useEffect(() => {
    if (!lectureData) return
    const nextSlide = currentSlide + 1
    if (nextSlide >= lectureData.total_slides) return

    const nextAudio = new Audio(`${API_URL}/api/v1/session/${sessionId}/audio/${nextSlide}`)
    nextAudio.preload = 'auto'
    nextAudio.load()
    prefetchAudioRef.current = nextAudio
  }, [currentSlide, sessionId, lectureData])

  const togglePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
        setIsPlaying(false)
      } else {
        setAudioLoading(true)
        audioRef.current.play().then(() => {
          setIsPlaying(true)
        }).catch(() => {
          setIsPlaying(false)
          setAudioLoading(false)
        })
      }
    }
  }

  const nextSlide = () => {
    if (lectureData && currentSlide < lectureData.total_slides - 1) {
      setCurrentSlide(currentSlide + 1)
    }
  }

  const previousSlide = () => {
    if (currentSlide > 0) {
      setCurrentSlide(currentSlide - 1)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleProgressBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || duration === 0) return

    const rect = e.currentTarget.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const percentage = clickX / rect.width
    const newTime = percentage * duration

    audioRef.current.currentTime = newTime
    setCurrentTime(newTime)
  }

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  const handleMouseMove = () => {
    if (!isFullscreen) return

    setShowControls(true)

    // Clear existing timeout
    if (hideControlsTimeout.current) {
      clearTimeout(hideControlsTimeout.current)
    }

    // Hide controls after 3 seconds of no movement
    hideControlsTimeout.current = setTimeout(() => {
      setShowControls(false)
    }, 3000)
  }

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
      if (!document.fullscreenElement) {
        setShowControls(true)
        if (hideControlsTimeout.current) {
          clearTimeout(hideControlsTimeout.current)
        }
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      if (hideControlsTimeout.current) {
        clearTimeout(hideControlsTimeout.current)
      }
    }
  }, [])

  const handleTimeUpdate = () => {
    if (audioRef.current && lectureData) {
      const time = audioRef.current.currentTime
      const dur = audioRef.current.duration || 0

      setCurrentTime(time)
      setDuration(dur)

      // Only show subtitles if we have precise word timings
      if (dur > 0 && lectureData.word_timings?.[currentSlide]?.length > 0) {
        const timings = lectureData.word_timings[currentSlide]

        // Find current timing index based on time
        let currentIndex = 0
        for (let i = 0; i < timings.length; i++) {
          if (time >= timings[i].start_time) {
            currentIndex = i
          } else {
            break
          }
        }

        // Check if this looks like sentence-level timing (long "words")
        const avgWordLength = timings.map(t => t.word.length).reduce((a, b) => a + b, 0) / timings.length
        const isSentenceLevel = avgWordLength > 50  // Sentences are typically >50 chars

        if (isSentenceLevel) {
          // Show just the current sentence (sentence-level timing from Edge TTS)
          setCurrentSubtitle(timings[currentIndex]?.word || '')
        } else {
          // Show chunk of ~15 words (word-level timing from Google TTS)
          const WORDS_PER_CHUNK = 15
          const chunkStartIndex = Math.floor(currentIndex / WORDS_PER_CHUNK) * WORDS_PER_CHUNK
          const chunkEndIndex = Math.min(chunkStartIndex + WORDS_PER_CHUNK, timings.length)
          const chunkWords = timings.slice(chunkStartIndex, chunkEndIndex).map(t => t.word)
          setCurrentSubtitle(chunkWords.join(' '))
        }
      } else {
        // No precise timings - no subtitles
        setCurrentSubtitle('')
      }
    }
  }

  const handleAudioEnded = () => {
    setIsPlaying(false)
    if (lectureData && currentSlide < lectureData.total_slides - 1) {
      setTimeout(() => {
        setCurrentSlide(currentSlide + 1)
        setTimeout(() => {
          if (audioRef.current) {
            audioRef.current.play()
            setIsPlaying(true)
          }
        }, 500)
      }, 1000)
    }
  }

  const handleAudioLoadStart = () => {
    setAudioLoading(true)
    setAudioError(null)
  }

  const handleAudioWaiting = () => {
    setAudioLoading(true)
  }

  const handleAudioCanPlay = () => {
    setAudioLoading(false)
  }

  const handleAudioPlaying = () => {
    setAudioLoading(false)
    setAudioError(null)
  }

  const handleAudioError = () => {
    setAudioLoading(false)
    setIsPlaying(false)
    setAudioError('Audio failed to load. Please try again.')
  }

  if (!lectureData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
          <p className="text-xl text-gray-400">Loading lecture...</p>
        </div>
      </div>
    )
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div ref={containerRef} className="relative min-h-screen bg-black text-white overflow-hidden" onMouseMove={handleMouseMove}>
      {/* Ambient background */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900/10 via-purple-900/10 to-black"></div>
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative flex flex-col h-screen">
        {/* Header - hide in fullscreen */}
        {!isFullscreen && (
        <header className="relative z-10 bg-black/40 backdrop-blur-xl border-b border-white/10">
          <div className="px-8 py-6 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">{lectureData.pdf_name}</h1>
                <p className="text-sm text-gray-400">AI Lecture Viewer</p>
              </div>
            </div>

            <button
              onClick={() => setShowTranscript(!showTranscript)}
              className="group relative px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all"
            >
              <span className="flex items-center space-x-2 text-sm font-semibold">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>{showTranscript ? 'Hide' : 'Show'} Transcript</span>
              </span>
            </button>
          </div>
        </header>
        )}

        {/* Main content */}
        <div className="relative flex-1 flex overflow-hidden">
          {/* Slide viewer */}
          <div className={`relative flex items-center justify-center transition-all duration-300 ${
            isFullscreen ? 'w-full p-0' : (showTranscript ? 'w-2/3 p-12' : 'w-full p-12')
          }`}>
            {/* Slide card */}
            <div className="relative w-full h-full max-w-6xl flex flex-col">
              <div className={`absolute inset-0 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-3xl blur-2xl opacity-50 ${isFullscreen ? 'hidden' : ''}`}></div>
              <div className={`relative flex-1 bg-black/40 backdrop-blur-xl border border-white/20 shadow-2xl overflow-hidden ${isFullscreen ? 'rounded-none border-0' : 'rounded-3xl p-4'}`}>
                <img
                  src={`${API_URL}/api/v1/session/${sessionId}/slide/${currentSlide}`}
                  alt={`Slide ${currentSlide + 1}`}
                  className="w-full h-full object-contain"
                />

                {(audioLoading || audioError) && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                    <div className="flex items-center space-x-3 bg-black/60 border border-white/10 rounded-xl px-5 py-3">
                      {audioError ? (
                        <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      ) : (
                        <div className="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
                      )}
                      <span className="text-sm text-gray-200">
                        {audioError ? audioError : 'Loading audio...'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Subtitles - overlay inside slide */}
                {isPlaying && currentSubtitle && (
                  <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-[90%] max-w-4xl bg-black/50 rounded-lg px-6 py-3 transition-all duration-300">
                    <p className="text-white text-base text-center leading-relaxed font-medium">
                      {currentSubtitle}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Transcript panel - hide in fullscreen */}
          {!isFullscreen && (
          <div className={`absolute right-0 top-0 h-full bg-black/60 backdrop-blur-2xl border-l border-white/10 transition-all duration-300 overflow-hidden ${
            showTranscript ? 'w-1/3' : 'w-0'
          }`}>
            {showTranscript && (
              <div className="h-full flex flex-col">
                <div className="p-8 border-b border-white/10">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                    <h2 className="text-lg font-bold text-white">Transcript</h2>
                  </div>
                  <p className="text-sm text-blue-400 font-medium">
                    Slide {currentSlide + 1}: {lectureData.slide_titles?.[currentSlide] || `Slide ${currentSlide + 1}`}
                  </p>
                </div>
                <div className="flex-1 overflow-y-auto p-8">
                  <p className="text-gray-300 leading-relaxed text-lg">
                    {lectureData.narrations?.[currentSlide] || 'No transcript available for this slide.'}
                  </p>
                </div>
              </div>
            )}
          </div>
          )}
        </div>

        {/* Controls */}
        <div className={`relative z-10 bg-black/60 backdrop-blur-2xl border-t border-white/10 transition-all duration-300 ${
          isFullscreen ? (showControls ? 'translate-y-0' : 'translate-y-full') : ''
        } ${isFullscreen ? 'absolute bottom-0 left-0 right-0' : ''}`}>
          <div className="px-8 py-6 space-y-6">
            {/* Progress bar */}
            <div className="relative">
              <div
                className="w-full h-2 bg-white/10 rounded-full overflow-hidden cursor-pointer hover:h-3 transition-all"
                onClick={handleProgressBarClick}
              >
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-100 rounded-full pointer-events-none"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <div className="absolute -top-1 left-0 right-0 flex justify-between text-xs text-gray-400 font-mono">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Control buttons */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={previousSlide}
                  disabled={currentSlide === 0}
                  className="group relative px-5 py-3 bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed border border-white/10 rounded-xl transition-all disabled:hover:bg-white/5"
                >
                  <div className="flex items-center space-x-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                    </svg>
                    <span className="font-semibold text-sm">Previous</span>
                  </div>
                </button>

                <button
                  onClick={togglePlayPause}
                  className="relative px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 rounded-xl transition-all transform hover:scale-105 shadow-lg shadow-blue-500/25"
                >
                  <div className="flex items-center space-x-3">
                    {isPlaying ? (
                      <>
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-bold">Pause</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-bold">Play</span>
                      </>
                    )}
                  </div>
                </button>

                <button
                  onClick={nextSlide}
                  disabled={currentSlide === lectureData.total_slides - 1}
                  className="group relative px-5 py-3 bg-white/5 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed border border-white/10 rounded-xl transition-all disabled:hover:bg-white/5"
                >
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-sm">Next</span>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                    </svg>
                  </div>
                </button>
              </div>

              <div className="flex items-center space-x-8">
                <div className="flex items-center space-x-3 bg-white/5 px-5 py-3 rounded-xl border border-white/10">
                  <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="text-lg font-mono">
                    <span className="text-white font-bold">{currentSlide + 1}</span>
                    <span className="text-gray-400"> / </span>
                    <span className="text-gray-400">{lectureData.total_slides}</span>
                  </span>
                </div>

                <button
                  onClick={toggleFullscreen}
                  className="flex items-center space-x-2 bg-white/5 hover:bg-white/10 px-5 py-3 rounded-xl border border-white/10 transition-all"
                >
                  {isFullscreen ? (
                    <>
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span className="text-sm font-semibold">Exit Fullscreen</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                      </svg>
                      <span className="text-sm font-semibold">Fullscreen</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleAudioEnded}
        onLoadedMetadata={handleTimeUpdate}
        onLoadStart={handleAudioLoadStart}
        onWaiting={handleAudioWaiting}
        onCanPlay={handleAudioCanPlay}
        onCanPlayThrough={handleAudioCanPlay}
        onPlaying={handleAudioPlaying}
        onError={handleAudioError}
      />
    </div>
  )
}
