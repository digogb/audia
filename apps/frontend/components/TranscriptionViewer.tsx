'use client'

import { useState } from 'react'

interface Phrase {
  speaker: number
  text: string
  start_time: number
  end_time: number
  confidence: number
}

interface TranscriptionViewerProps {
  fullText: string
  phrases: Phrase[]
  speakerNames?: Record<string, string>
  onTimeClick?: (time: number) => void
}

const SPEAKER_COLORS = [
  'bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-200',
  'bg-green-100 dark:bg-green-900/30 text-green-900 dark:text-green-200',
  'bg-violet-100 dark:bg-violet-900/30 text-violet-900 dark:text-violet-200',
  'bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-200',
  'bg-pink-100 dark:bg-pink-900/30 text-pink-900 dark:text-pink-200',
]

export default function TranscriptionViewer({
  fullText,
  phrases,
  speakerNames,
  onTimeClick,
}: TranscriptionViewerProps) {
  const [view, setView] = useState<'simple' | 'detailed'>('detailed')
  const [searchTerm, setSearchTerm] = useState('')

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getSpeakerColor = (speakerId: number): string => {
    return SPEAKER_COLORS[speakerId % SPEAKER_COLORS.length]
  }

  const getSpeakerName = (speakerId: number): string => {
    // speakerId já vem com o valor correto (1, 2, 3...), não precisa somar 1
    const speakerIdStr = speakerId.toString()
    return speakerNames?.[speakerIdStr] || `Speaker ${speakerId}`
  }

  const highlightSearch = (text: string): JSX.Element => {
    if (!searchTerm.trim()) return <>{text}</>

    const regex = new RegExp(`(${searchTerm})`, 'gi')
    const parts = text.split(regex)

    return (
      <>
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-yellow-200 dark:bg-yellow-700 rounded px-1">
              {part}
            </mark>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </>
    )
  }

  const filterPhrases = (phrases: Phrase[]): Phrase[] => {
    if (!searchTerm.trim()) return phrases

    return phrases.filter(phrase =>
      phrase.text.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }

  const filterText = (text: string): string => {
    if (!searchTerm.trim()) return text

    // Divide o texto em parágrafos e filtra apenas os que contêm o termo
    const paragraphs = text.split('\n\n')
    const filtered = paragraphs.filter(p =>
      p.toLowerCase().includes(searchTerm.toLowerCase())
    )

    return filtered.length > 0 ? filtered.join('\n\n') : 'Nenhum resultado encontrado'
  }

  const removesSpeakerPrefixes = (text: string): string => {
    // Remove prefixos "Nome: " ou "Speaker X: " do início de cada sentença
    return text.replace(/(?:^|\s)([A-Za-z0-9\s]+):\s/g, ' ').trim()
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <span className="text-xl">📝</span>
            Transcrição
          </h3>

          {/* View toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setView('simple')}
              className={`btn-sm ${view === 'simple' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Simples
            </button>
            <button
              onClick={() => setView('detailed')}
              className={`btn-sm ${view === 'detailed' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Detalhada
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Buscar na transcrição..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input pl-10"
          />
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 md:p-6 max-h-[600px] overflow-y-auto">
        {view === 'simple' ? (
          /* Simple view */
          <div className="prose dark:prose-invert max-w-none">
            <p className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">
              {highlightSearch(removesSpeakerPrefixes(filterText(fullText)))}
            </p>
          </div>
        ) : (
          /* Detailed view with diarization */
          <div className="space-y-4">
            {filterPhrases(phrases).length > 0 ? (
              filterPhrases(phrases).map((phrase, index) => (
                <div
                  key={index}
                  className={`rounded-lg p-4 ${getSpeakerColor(phrase.speaker)} transition-all hover:shadow-md`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">
                        {getSpeakerName(phrase.speaker)}
                      </span>
                      <span className="text-xs opacity-70">
                        {(phrase.confidence * 100).toFixed(0)}% confiança
                      </span>
                    </div>

                    <button
                      onClick={() => onTimeClick?.(phrase.start_time)}
                      className="text-xs font-mono opacity-70 hover:opacity-100 transition-opacity flex items-center gap-1"
                    >
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
                      </svg>
                      {formatTime(phrase.start_time)} - {formatTime(phrase.end_time)}
                    </button>
                  </div>

                  <p className="text-sm leading-relaxed">
                    {highlightSearch(phrase.text)}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-center text-slate-500 dark:text-slate-400 py-8">
                Nenhum resultado encontrado
              </p>
            )}
          </div>
        )}
      </div>

      {/* Footer stats */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-400">
        {searchTerm.trim() && (
          <div className="text-blue-600 dark:text-blue-400 font-semibold">
            {view === 'detailed' ? (
              <>
                <strong className="text-blue-700 dark:text-blue-300">
                  {filterPhrases(phrases).length}
                </strong>{' '}
                de {phrases.length} frases encontradas
              </>
            ) : (
              <>
                Filtrando por "{searchTerm}"
              </>
            )}
          </div>
        )}
        <div>
          <strong className="text-slate-900 dark:text-slate-100">
            {phrases.length}
          </strong>{' '}
          frases
        </div>
        <div>
          <strong className="text-slate-900 dark:text-slate-100">
            {new Set(phrases.map((p) => p.speaker)).size}
          </strong>{' '}
          speakers
        </div>
        <div>
          <strong className="text-slate-900 dark:text-slate-100">
            {fullText.split(' ').length}
          </strong>{' '}
          palavras
        </div>
      </div>
    </div>
  )
}
