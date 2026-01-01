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
  narrations_tts?: Record<string, string>
  slide_titles: string[]
  word_timings: Record<string, WordTiming[]>
  display_sentences?: Record<string, string[]>
  tts_provider?: string
  polly_voice?: string
  enable_vision?: boolean
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
  const [showSubtitles, setShowSubtitles] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioError, setAudioError] = useState<string | null>(null)
  const [slideError, setSlideError] = useState<string | null>(null)
  const [slideCacheBuster, setSlideCacheBuster] = useState(0)

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

  useEffect(() => {
    setSlideError(null)
    setSlideCacheBuster(0)
  }, [currentSlide])

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
      const isNowFullscreen = !!document.fullscreenElement
      setIsFullscreen(isNowFullscreen)
      if (!isNowFullscreen) {
        setShowControls(true)
        if (hideControlsTimeout.current) {
          clearTimeout(hideControlsTimeout.current)
        }
      } else {
        setShowControls(false)
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
          const displaySentences = lectureData.display_sentences?.[currentSlide]
          // Show just the current sentence (sentence-level timing from Edge TTS)
          if (displaySentences && displaySentences[currentIndex]) {
            setCurrentSubtitle(displaySentences[currentIndex])
          } else {
            setCurrentSubtitle(timings[currentIndex]?.word || '')
          }
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

  const handleSlideError = () => {
    setSlideError('Slide failed to load. Please retry.')
  }

  const retryAudio = () => {
    if (!audioRef.current) return
    setAudioError(null)
    setAudioLoading(true)
    audioRef.current.load()
    audioRef.current.play().then(() => {
      setIsPlaying(true)
    }).catch(() => {
      setAudioLoading(false)
    })
  }

  const retrySlide = () => {
    setSlideError(null)
    setSlideCacheBuster((value) => value + 1)
  }

  if (!lectureData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-sky-100">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-2 border-sky-200 border-t-sky-500 rounded-full animate-spin"></div>
          <p className="text-lg text-slate-600">Loading lecture...</p>
        </div>
      </div>
    )
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0
  const providerLabel = (() => {
    if (!lectureData?.tts_provider) return null
    if (lectureData.tts_provider === 'polly') {
      return `Voice: Polly${lectureData.polly_voice ? ` (${lectureData.polly_voice})` : ''}`
    }
    if (lectureData.tts_provider === 'edge') {
      return 'Voice: Edge TTS'
    }
    return `Voice: ${lectureData.tts_provider}`
  })()
  const visionLabel = lectureData?.enable_vision === undefined
    ? null
    : `Vision: ${lectureData.enable_vision ? 'On' : 'Off'}`

  return (
    <div ref={containerRef} className="relative min-h-screen bg-sky-100 text-slate-900 overflow-hidden" onMouseMove={handleMouseMove}>

      <div className="relative flex flex-col h-screen">
        {/* Header - hide in fullscreen */}
        {!isFullscreen && (
        <header className="relative z-10 bg-white/90 backdrop-blur border-b border-slate-200">
          <div className="px-6 py-3 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-8 h-8 bg-slate-900 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h1 className="text-sm font-semibold text-slate-900">{lectureData.pdf_name}</h1>
                <p className="text-xs text-slate-500">
                  {['Lecture Viewer', providerLabel, visionLabel].filter(Boolean).join(' • ')}
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowTranscript(!showTranscript)}
              className="group relative px-3 py-1.5 bg-white border border-slate-200 rounded-md text-slate-700 hover:text-slate-900 hover:border-slate-300 transition-colors"
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
          <div className={`relative flex justify-center transition-all duration-300 ${
            isFullscreen ? 'w-full p-0 items-stretch' : 'items-center'
          } ${showTranscript && !isFullscreen ? 'w-[calc(100%-360px)] p-8' : (!isFullscreen ? 'w-full p-8' : '')}`}>
            {/* Slide card */}
            <div className={`relative w-full h-full flex flex-col ${isFullscreen ? 'max-w-none' : 'max-w-6xl'}`}>
              <div className={`relative flex-1 bg-slate-50 border border-slate-200 shadow-md overflow-hidden ${isFullscreen ? 'rounded-none border-0 p-0' : 'rounded-2xl p-3'}`}>
                <img
                  src={`${API_URL}/api/v1/session/${sessionId}/slide/${currentSlide}?v=${slideCacheBuster}`}
                  alt={`Slide ${currentSlide + 1}`}
                  className={`${isFullscreen ? 'h-full w-auto mx-auto rounded-none' : 'w-full h-full object-contain rounded-lg'} bg-slate-50`}
                  onError={handleSlideError}
                />

                {(audioLoading || audioError || slideError) && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white/70">
                    <div className="flex items-center space-x-3 bg-white border border-slate-200 rounded-lg px-5 py-3">
                      {(audioError || slideError) ? (
                        <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      ) : (
                        <div className="w-4 h-4 border-2 border-sky-300 border-t-sky-600 rounded-full animate-spin"></div>
                      )}
                      <span className="text-sm text-slate-700">
                        {audioError || slideError || 'Loading audio...'}
                      </span>
                      {audioError && (
                        <button
                          onClick={retryAudio}
                          className="ml-2 text-xs font-semibold text-sky-700 hover:text-sky-800 transition-colors"
                        >
                          Retry
                        </button>
                      )}
                      {slideError && (
                        <button
                          onClick={retrySlide}
                          className="ml-2 text-xs font-semibold text-sky-700 hover:text-sky-800 transition-colors"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Subtitles - overlay inside slide */}
                {isPlaying && showSubtitles && currentSubtitle && (
                  <div className={`absolute left-1/2 -translate-x-1/2 w-[90%] max-w-4xl bg-white/90 border border-slate-200 rounded-lg px-5 py-2.5 transition-all duration-300 ${
                    isFullscreen ? (showControls ? 'bottom-6' : 'bottom-2') : 'bottom-4'
                  }`}>
                    <p className="text-slate-800 text-sm text-center leading-relaxed font-medium">
                      {currentSubtitle}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Transcript panel - hide in fullscreen */}
          {!isFullscreen && (
          <div className={`absolute right-0 top-0 h-full bg-white border-l border-slate-200 transition-all duration-300 overflow-hidden ${
            showTranscript ? 'w-[360px]' : 'w-0'
          }`}>
            {showTranscript && (
              <div className="h-full flex flex-col">
                <div className="p-6 border-b border-slate-200">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-2 h-2 bg-sky-500 rounded-full animate-pulse"></div>
                    <h2 className="text-base font-semibold text-slate-900">Transcript</h2>
                  </div>
                  <p className="text-xs text-slate-600 font-medium">
                    Slide {currentSlide + 1}: {lectureData.slide_titles?.[currentSlide] || `Slide ${currentSlide + 1}`}
                  </p>
                </div>
                <div className="flex-1 overflow-y-auto p-6">
                  <p className="text-slate-700 leading-relaxed text-base">
                    {lectureData.narrations?.[currentSlide] || 'No transcript available for this slide.'}
                  </p>
                </div>
              </div>
            )}
          </div>
          )}
        </div>

        {/* Controls */}
        <div className={`relative z-10 transition-all duration-300 ${
          isFullscreen ? (showControls ? 'translate-y-0' : 'translate-y-[120%]') : ''
        } ${isFullscreen ? 'absolute bottom-0 left-0 right-0' : 'pb-6'}`}>
          <div className={`max-w-5xl mx-auto border border-slate-200 rounded-2xl px-5 py-4 space-y-3 shadow-sm backdrop-blur ${
            isFullscreen ? 'bg-white/80' : 'bg-white'
          }`}>
            {/* Progress bar */}
            <div className="relative">
              <div
                className="w-full h-2 bg-slate-100 rounded-full overflow-hidden cursor-pointer hover:h-3 transition-all"
                onClick={handleProgressBarClick}
              >
                <div
                  className="h-full bg-sky-500 transition-all duration-100 rounded-full pointer-events-none"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <div className="absolute -top-1 left-0 right-0 flex justify-between text-xs text-slate-500 font-mono">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Control buttons */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <button
                  onClick={previousSlide}
                  disabled={currentSlide === 0}
                  className="group relative px-3 py-2 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-200 rounded-lg transition-colors"
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
                  className="relative px-6 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg transition-colors"
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
                  onClick={() => setShowSubtitles(prev => !prev)}
                  aria-pressed={showSubtitles}
                  className={`px-3 py-2 border rounded-lg text-xs font-semibold tracking-wide transition-colors ${
                    showSubtitles
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  CC
                </button>

                <button
                  onClick={nextSlide}
                  disabled={currentSlide === lectureData.total_slides - 1}
                  className="group relative px-3 py-2 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-200 rounded-lg transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-sm">Next</span>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                    </svg>
                  </div>
                </button>
              </div>

              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-3 bg-white px-4 py-2 rounded-lg border border-slate-200">
                  <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="text-base font-mono">
                    <span className="text-slate-900 font-bold">{currentSlide + 1}</span>
                    <span className="text-slate-400"> / </span>
                    <span className="text-slate-400">{lectureData.total_slides}</span>
                  </span>
                </div>

                <button
                  onClick={toggleFullscreen}
                  className="flex items-center space-x-2 bg-white hover:bg-slate-50 px-4 py-2 rounded-lg border border-slate-200 transition-colors"
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
