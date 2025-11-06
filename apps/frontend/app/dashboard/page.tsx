'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'
import api from '@/lib/api-client'
import Navbar from '@/components/Navbar'

interface Transcription {
  job_id: string
  filename: string
  status: string
  progress: number
  duration_seconds?: number
  created_at: string
  completed_at?: string
}

export default function DashboardPage() {
  const router = useRouter()
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('ALL')

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }

    loadTranscriptions()
    // Poll a cada 10 segundos para atualizar status
    const interval = setInterval(loadTranscriptions, 10000)
    return () => clearInterval(interval)
  }, [router, filter])

  const loadTranscriptions = async () => {
    try {
      const params = filter !== 'ALL' ? { status_filter: filter } : {}
      const response = await api.transcriptions.list(params)
      setTranscriptions(response.data.items)
    } catch (error) {
      console.error('Erro ao carregar transcrições:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string, progress: number) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="badge-success">✓ Completo</span>
      case 'PROCESSING':
        return (
          <span className="badge-info flex items-center gap-1">
            <span className="spinner w-3 h-3"></span>
            Processando {Math.round(progress * 100)}%
          </span>
        )
      case 'QUEUED':
        return <span className="badge-warning">⏳ Na fila</span>
      case 'FAILED':
        return <span className="badge-error">✗ Falhou</span>
      default:
        return <span className="badge">{status}</span>
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
        <Navbar />
        <div className="container-custom py-8">
          <div className="flex items-center justify-center h-64">
            <div className="spinner w-12 h-12"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <Navbar />

      <div className="container-custom py-6 md:py-8">
        {/* Header */}
        <div className="mb-6 md:mb-8">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            📊 Dashboard
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Gerencie suas transcrições
          </p>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="card p-4">
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Total</p>
            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              {transcriptions.length}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Completas</p>
            <p className="text-2xl font-bold text-green-600">
              {transcriptions.filter((t) => t.status === 'COMPLETED').length}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Processando</p>
            <p className="text-2xl font-bold text-blue-600">
              {transcriptions.filter((t) => t.status === 'PROCESSING').length}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Falharam</p>
            <p className="text-2xl font-bold text-red-600">
              {transcriptions.filter((t) => t.status === 'FAILED').length}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-6">
          {['ALL', 'COMPLETED', 'PROCESSING', 'QUEUED', 'FAILED'].map((status) => {
            const labels: Record<string, string> = {
              'ALL': 'Todas',
              'COMPLETED': 'Completas',
              'PROCESSING': 'Processando',
              'QUEUED': 'Na Fila',
              'FAILED': 'Falharam'
            }

            return (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`btn-sm ${
                  filter === status
                    ? 'btn-primary'
                    : 'btn-secondary'
                }`}
              >
                {labels[status]}
              </button>
            )
          })}
        </div>

        {/* Empty state */}
        {transcriptions.length === 0 ? (
          <div className="card p-12 text-center">
            <div className="w-20 h-20 mx-auto mb-4 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center">
              <span className="text-4xl">🎙️</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Nenhuma transcrição ainda
            </h3>
            <p className="text-slate-600 dark:text-slate-400 mb-6">
              Faça upload do seu primeiro áudio para começar
            </p>
            <button
              onClick={() => router.push('/upload')}
              className="btn-primary btn-md"
            >
              ➕ Fazer Upload
            </button>
          </div>
        ) : (
          /* List */
          <div className="space-y-3">
            {transcriptions.map((item) => (
              <div
                key={item.job_id}
                onClick={() =>
                  item.status === 'COMPLETED' && router.push(`/transcription/${item.job_id}`)
                }
                className={`card p-4 md:p-6 ${
                  item.status === 'COMPLETED' ? 'card-hover' : ''
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center gap-4">
                  {/* Icon */}
                  <div className="hidden md:flex w-12 h-12 bg-gradient-to-br from-blue-500 to-violet-500 rounded-lg items-center justify-center flex-shrink-0">
                    <span className="text-2xl">🎵</span>
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100 truncate mb-1">
                      {item.filename}
                    </h3>
                    <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                      <span>{formatDate(item.created_at)}</span>
                      {item.duration_seconds && (
                        <>
                          <span>•</span>
                          <span>{formatDuration(item.duration_seconds)}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Status */}
                  <div className="flex items-center gap-3">
                    {getStatusBadge(item.status, item.progress)}
                    {item.status === 'COMPLETED' && (
                      <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    )}
                  </div>
                </div>

                {/* Progress bar for processing */}
                {item.status === 'PROCESSING' && (
                  <div className="mt-3 w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-blue-600 h-full transition-all duration-300"
                      style={{ width: `${item.progress * 100}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Floating action button (mobile) */}
      <button
        onClick={() => router.push('/upload')}
        className="md:hidden fixed bottom-6 right-6 w-14 h-14 rounded-full gradient-primary text-white shadow-lg flex items-center justify-center text-2xl hover:scale-110 transition-transform"
      >
        ➕
      </button>
    </div>
  )
}
