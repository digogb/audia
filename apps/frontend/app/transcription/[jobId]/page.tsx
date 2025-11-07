'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'
import api from '@/lib/api-client'
import Navbar from '@/components/Navbar'
import Chat from '@/components/Chat'
import TranscriptionViewer from '@/components/TranscriptionViewer'

interface Transcription {
  job_id: string
  filename: string
  full_text: string
  duration_seconds: number
  phrases: any[]
  speakers: any[]
  created_at: string
  completed_at: string
}

export default function TranscriptionPage() {
  const router = useRouter()
  const params = useParams()
  const jobId = params.jobId as string

  const [transcription, setTranscription] = useState<Transcription | null>(null)
  const [summary, setSummary] = useState<string | null>(null)
  const [meetingMinutes, setMeetingMinutes] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [loadingMinutes, setLoadingMinutes] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [activeTab, setActiveTab] = useState<'transcription' | 'chat'>('transcription')
  const [summaryExpanded, setSummaryExpanded] = useState(true)
  const [minutesExpanded, setMinutesExpanded] = useState(true)

  // Edição
  const [editingMode, setEditingMode] = useState<'speakers' | 'text' | null>(null)
  const [speakerNames, setSpeakerNames] = useState<Record<string, string>>({})
  const [editedText, setEditedText] = useState<string>('')
  const [savingChanges, setSavingChanges] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }

    loadTranscription()
    loadSummary()
    loadMeetingMinutes()
  }, [jobId, router])

  const loadTranscription = async () => {
    try {
      const response = await api.transcriptions.get(jobId)
      setTranscription(response.data)
    } catch (error: any) {
      console.error('Erro ao carregar transcrição:', error)
      if (error.response?.status === 404) {
        alert('Transcrição não encontrada')
        router.push('/dashboard')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadSummary = async () => {
    try {
      const response = await api.summary.get(jobId)
      setSummary(response.data.summary)
    } catch (error) {
      // Summary não existe ainda, tudo bem
    }
  }

  const loadMeetingMinutes = async () => {
    try {
      const response = await api.meetingMinutes.get(jobId)
      setMeetingMinutes(response.data.meeting_minutes)
    } catch (error) {
      // Ata não existe ainda, tudo bem
    }
  }

  const generateSummary = async () => {
    setLoadingSummary(true)
    try {
      const response = await api.summary.generate(jobId)
      setSummary(response.data.summary)

      // Se foi enfileirado, fazer polling
      if (!response.data.cached) {
        const interval = setInterval(async () => {
          try {
            const res = await api.summary.get(jobId)
            if (res.data.summary && !res.data.summary.includes('sendo gerado')) {
              setSummary(res.data.summary)
              clearInterval(interval)
              setLoadingSummary(false)
            }
          } catch (error) {
            // Continuar tentando
          }
        }, 5000)

        // Timeout após 2 minutos
        setTimeout(() => {
          clearInterval(interval)
          setLoadingSummary(false)
        }, 120000)
      } else {
        setLoadingSummary(false)
      }
    } catch (error) {
      console.error('Erro ao gerar resumo:', error)
      setLoadingSummary(false)
    }
  }

  const generateMeetingMinutes = async () => {
    setLoadingMinutes(true)
    try {
      const response = await api.meetingMinutes.generate(jobId)
      setMeetingMinutes(response.data.meeting_minutes)

      // Se foi enfileirado, fazer polling
      if (!response.data.cached) {
        const interval = setInterval(async () => {
          try {
            const res = await api.meetingMinutes.get(jobId)
            if (res.data.meeting_minutes && res.data.meeting_minutes.title !== 'Gerando...') {
              setMeetingMinutes(res.data.meeting_minutes)
              clearInterval(interval)
              setLoadingMinutes(false)
            }
          } catch (error) {
            // Continuar tentando
          }
        }, 5000)

        // Timeout após 2 minutos
        setTimeout(() => {
          clearInterval(interval)
          setLoadingMinutes(false)
        }, 120000)
      } else {
        setLoadingMinutes(false)
      }
    } catch (error) {
      console.error('Erro ao gerar ata de reunião:', error)
      setLoadingMinutes(false)
    }
  }

  const startEditingSpeakers = () => {
    if (!transcription) return
    // Inicializar com nomes padrão (Speaker 1, Speaker 2, etc.)
    const initialNames: Record<string, string> = {}
    transcription.speakers.forEach((speaker) => {
      initialNames[speaker.speaker_id.toString()] = `Speaker ${speaker.speaker_id}`
    })
    setSpeakerNames(initialNames)
    setEditingMode('speakers')
  }

  const startEditingText = () => {
    if (!transcription) return
    setEditedText(transcription.full_text)
    setEditingMode('text')
  }

  const cancelEditing = () => {
    setEditingMode(null)
    setSpeakerNames({})
    setEditedText('')
  }

  const saveSpeakerNames = async () => {
    setSavingChanges(true)
    try {
      await api.transcriptions.updateSpeakers(jobId, speakerNames)

      // Atualizar transcrição localmente sem recarregar
      if (transcription) {
        const updatedTranscription = { ...transcription }

        // Atualizar speakers com os novos nomes
        updatedTranscription.speakers = transcription.speakers.map(speaker => ({
          ...speaker,
          texts: speaker.texts.map((text: string) =>
            text.replace(
              `Speaker ${speaker.speaker_id}`,
              speakerNames[speaker.speaker_id.toString()] || `Speaker ${speaker.speaker_id}`
            )
          )
        }))

        // Atualizar full_text
        let updatedFullText = transcription.full_text
        Object.entries(speakerNames).forEach(([speakerId, customName]) => {
          const regex = new RegExp(`Speaker ${speakerId}`, 'g')
          updatedFullText = updatedFullText.replace(regex, customName)
        })
        updatedTranscription.full_text = updatedFullText

        setTranscription(updatedTranscription)
      }

      alert('Nomes dos speakers atualizados com sucesso!')
      setEditingMode(null)
    } catch (error) {
      console.error('Erro ao salvar nomes:', error)
      alert('Erro ao salvar nomes dos speakers')
    } finally {
      setSavingChanges(false)
    }
  }

  const saveEditedText = async () => {
    setSavingChanges(true)
    try {
      await api.transcriptions.updateText(jobId, editedText)

      // Atualizar transcrição localmente sem recarregar
      if (transcription) {
        setTranscription({
          ...transcription,
          full_text: editedText
        })
      }

      alert('Transcrição editada com sucesso!')
      setEditingMode(null)
    } catch (error) {
      console.error('Erro ao salvar transcrição:', error)
      alert('Erro ao salvar transcrição editada')
    } finally {
      setSavingChanges(false)
    }
  }

  const downloadTranscription = async (format: 'txt' | 'json') => {
    setDownloading(true)
    try {
      const response = await api.transcriptions.download(jobId, format)
      const blob = new Blob([response.data], {
        type: format === 'json' ? 'application/json' : 'text/plain',
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${transcription?.filename || 'transcricao'}.${format}`
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Erro ao baixar:', error)
      alert('Erro ao baixar transcrição')
    } finally {
      setDownloading(false)
    }
  }

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    const hours = Math.floor(mins / 60)
    const remainingMins = mins % 60

    if (hours > 0) {
      return `${hours}h ${remainingMins}min`
    }
    return `${mins}min ${secs}s`
  }

  // Extrair nomes customizados dos speakers da transcrição
  const getSpeakerNamesFromTranscription = (): Record<string, string> | undefined => {
    if (!transcription) return undefined

    const customNames: Record<string, string> = {}
    transcription.speakers.forEach(speaker => {
      // Verificar se o texto do speaker foi customizado
      const firstText = speaker.texts[0] || ''
      const match = firstText.match(/^(.+?):\s/)
      if (match) {
        const speakerName = match[1]
        const defaultName = `Speaker ${speaker.speaker_id}`
        if (speakerName !== defaultName) {
          customNames[speaker.speaker_id.toString()] = speakerName
        }
      }
    })

    return Object.keys(customNames).length > 0 ? customNames : undefined
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
        <Navbar />
        <div className="container-custom py-12">
          <div className="flex flex-col items-center justify-center h-64">
            <div className="spinner w-12 h-12 mb-4"></div>
            <p className="text-slate-600 dark:text-slate-400">Carregando transcrição...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!transcription) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
        <Navbar />
        <div className="container-custom py-12 text-center">
          <p className="text-slate-600 dark:text-slate-400">Transcrição não encontrada</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <Navbar />

      <div className="container-custom py-6 md:py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/dashboard')}
            className="btn-ghost btn-sm mb-4"
          >
            ← Voltar ao Dashboard
          </button>

          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                {transcription.filename}
              </h1>
              <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {formatDuration(transcription.duration_seconds)}
                </span>
                <span>•</span>
                <span>{transcription.speakers.length} speakers</span>
                <span>•</span>
                <span>{transcription.phrases.length} frases</span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => downloadTranscription('txt')}
                disabled={downloading}
                className="btn-secondary btn-sm"
              >
                📄 TXT
              </button>
              <button
                onClick={() => downloadTranscription('json')}
                disabled={downloading}
                className="btn-secondary btn-sm"
              >
                📦 JSON
              </button>
              <button
                onClick={startEditingSpeakers}
                className="btn-secondary btn-sm"
                disabled={editingMode !== null}
              >
                👥 Editar Speakers
              </button>
              <button
                onClick={startEditingText}
                className="btn-secondary btn-sm"
                disabled={editingMode !== null}
              >
                ✏️ Editar Texto
              </button>
            </div>
          </div>
        </div>

        {/* Edit Speakers Modal */}
        {editingMode === 'speakers' && (
          <div className="card p-6 mb-6 border-2 border-blue-500">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <span className="text-xl">👥</span>
              Editar Nomes dos Speakers
            </h3>

            <div className="space-y-3 mb-4">
              {transcription.speakers.map((speaker) => (
                <div key={speaker.speaker_id} className="flex items-center gap-3">
                  <label className="text-sm font-medium text-slate-700 dark:text-slate-300 w-24">
                    Speaker {speaker.speaker_id}:
                  </label>
                  <input
                    type="text"
                    value={speakerNames[speaker.speaker_id.toString()] || ''}
                    onChange={(e) => setSpeakerNames({
                      ...speakerNames,
                      [speaker.speaker_id.toString()]: e.target.value
                    })}
                    className="input flex-1"
                    placeholder={`Nome do Speaker ${speaker.speaker_id}`}
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={saveSpeakerNames}
                disabled={savingChanges}
                className="btn-primary btn-sm"
              >
                {savingChanges ? 'Salvando...' : '💾 Salvar'}
              </button>
              <button
                onClick={cancelEditing}
                disabled={savingChanges}
                className="btn-secondary btn-sm"
              >
                ❌ Cancelar
              </button>
            </div>
          </div>
        )}

        {/* Edit Text Modal */}
        {editingMode === 'text' && (
          <div className="card p-6 mb-6 border-2 border-blue-500">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <span className="text-xl">✏️</span>
              Editar Transcrição
            </h3>

            <textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              className="input w-full h-96 font-mono text-sm"
              placeholder="Digite a transcrição editada..."
            />

            <div className="flex gap-2 mt-4">
              <button
                onClick={saveEditedText}
                disabled={savingChanges || !editedText.trim()}
                className="btn-primary btn-sm"
              >
                {savingChanges ? 'Salvando...' : '💾 Salvar'}
              </button>
              <button
                onClick={cancelEditing}
                disabled={savingChanges}
                className="btn-secondary btn-sm"
              >
                ❌ Cancelar
              </button>
            </div>
          </div>
        )}

        {/* Summary card */}
        <div className="card p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <span className="text-xl">📋</span>
              Resumo
            </h3>
            <div className="flex items-center gap-2">
              {summary && !loadingSummary && (
                <button
                  onClick={() => setSummaryExpanded(!summaryExpanded)}
                  className="btn-ghost btn-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                  title={summaryExpanded ? 'Minimizar' : 'Expandir'}
                >
                  {summaryExpanded ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  )}
                </button>
              )}
              {!summary && !loadingSummary && (
                <button
                  onClick={generateSummary}
                  className="btn-primary btn-sm"
                >
                  Gerar Resumo
                </button>
              )}
            </div>
          </div>

          {loadingSummary ? (
            <div className="flex items-center gap-3 text-slate-600 dark:text-slate-400">
              <div className="spinner w-5 h-5"></div>
              <span>Gerando resumo...</span>
            </div>
          ) : summary ? (
            summaryExpanded && (
              <p className="text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                {summary}
              </p>
            )
          ) : (
            <p className="text-slate-500 dark:text-slate-400 italic">
              Nenhum resumo gerado ainda. Clique em "Gerar Resumo" para criar um.
            </p>
          )}
        </div>

        {/* Meeting Minutes card */}
        <div className="card p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <span className="text-xl">📄</span>
              Ata de Reunião
            </h3>
            <div className="flex items-center gap-2">
              {meetingMinutes && !loadingMinutes && (
                <button
                  onClick={() => setMinutesExpanded(!minutesExpanded)}
                  className="btn-ghost btn-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                  title={minutesExpanded ? 'Minimizar' : 'Expandir'}
                >
                  {minutesExpanded ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  )}
                </button>
              )}
              {!meetingMinutes && !loadingMinutes && (
                <button
                  onClick={generateMeetingMinutes}
                  className="btn-primary btn-sm"
                >
                  Gerar Ata
                </button>
              )}
            </div>
          </div>

          {loadingMinutes ? (
            <div className="flex items-center gap-3 text-slate-600 dark:text-slate-400">
              <div className="spinner w-5 h-5"></div>
              <span>Gerando ata de reunião...</span>
            </div>
          ) : meetingMinutes ? (
            minutesExpanded && (
              <div className="space-y-6">
                {/* Title */}
                <div>
                  <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                    {meetingMinutes.title}
                  </h4>
                  <p className="text-slate-700 dark:text-slate-300">
                    {meetingMinutes.summary}
                  </p>
                </div>

                {/* Topics */}
                {meetingMinutes.topics && meetingMinutes.topics.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
                      <span>💬</span>
                      Tópicos Discutidos
                    </h5>
                    <div className="space-y-3">
                      {meetingMinutes.topics.map((topic: any, idx: number) => (
                        <div key={idx} className="bg-slate-50 dark:bg-slate-800 p-4 rounded-lg">
                          <h6 className="font-medium text-slate-900 dark:text-slate-100 mb-1">
                            {topic.topic}
                          </h6>
                          <p className="text-sm text-slate-600 dark:text-slate-400">
                            {topic.discussion}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Items */}
                {meetingMinutes.action_items && meetingMinutes.action_items.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
                      <span>✅</span>
                      Itens de Ação
                    </h5>
                    <div className="space-y-2">
                      {meetingMinutes.action_items.map((item: any, idx: number) => (
                        <div key={idx} className="flex items-start gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                          <span className="text-blue-600 dark:text-blue-400 font-bold text-sm">
                            {idx + 1}
                          </span>
                          <div className="flex-1">
                            <p className="text-slate-900 dark:text-slate-100 mb-1">
                              {item.item}
                            </p>
                            <div className="flex flex-wrap gap-3 text-sm">
                              <span className="text-slate-600 dark:text-slate-400">
                                <strong>Responsável:</strong> {item.responsible}
                              </span>
                              <span className="text-slate-600 dark:text-slate-400">
                                <strong>Prazo:</strong> {item.deadline}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Decisions */}
                {meetingMinutes.decisions && meetingMinutes.decisions.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
                      <span>⚖️</span>
                      Decisões
                    </h5>
                    <ul className="list-disc list-inside space-y-2 text-slate-700 dark:text-slate-300">
                      {meetingMinutes.decisions.map((decision: string, idx: number) => (
                        <li key={idx}>{decision}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Next Steps */}
                {meetingMinutes.next_steps && meetingMinutes.next_steps.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-slate-900 dark:text-slate-100 mb-3 flex items-center gap-2">
                      <span>🔜</span>
                      Próximos Passos
                    </h5>
                    <ul className="list-disc list-inside space-y-2 text-slate-700 dark:text-slate-300">
                      {meetingMinutes.next_steps.map((step: string, idx: number) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )
          ) : (
            <p className="text-slate-500 dark:text-slate-400 italic">
              Nenhuma ata de reunião gerada ainda. Clique em "Gerar Ata" para criar uma.
            </p>
          )}
        </div>

        {/* Mobile tabs */}
        <div className="lg:hidden flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('transcription')}
            className={`btn-sm flex-1 ${activeTab === 'transcription' ? 'btn-primary' : 'btn-secondary'}`}
          >
            📝 Transcrição
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`btn-sm flex-1 ${activeTab === 'chat' ? 'btn-primary' : 'btn-secondary'}`}
          >
            💬 Chat
          </button>
        </div>

        {/* Content */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Transcription */}
          <div className={activeTab === 'transcription' ? 'block' : 'hidden lg:block'}>
            <TranscriptionViewer
              fullText={transcription.full_text}
              phrases={transcription.phrases}
              speakerNames={getSpeakerNamesFromTranscription()}
            />
          </div>

          {/* Chat */}
          <div className={activeTab === 'chat' ? 'block' : 'hidden lg:block'}>
            <Chat jobId={jobId} />
          </div>
        </div>
      </div>
    </div>
  )
}
