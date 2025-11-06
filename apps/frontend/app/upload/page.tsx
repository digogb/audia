'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'
import Navbar from '@/components/Navbar'
import UploadZone from '@/components/UploadZone'

export default function UploadPage() {
  const router = useRouter()
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [jobId, setJobId] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
    }
  }, [router])

  const handleUploadComplete = (data: any) => {
    setUploadSuccess(true)
    setJobId(data.job_id)

    // Redirecionar para dashboard após 3 segundos
    setTimeout(() => {
      router.push('/dashboard')
    }, 3000)
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <Navbar />

      <div className="container-custom py-6 md:py-12">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8 md:mb-12">
            <h1 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-slate-100 mb-3">
              ➕ Novo Upload
            </h1>
            <p className="text-lg text-slate-600 dark:text-slate-400">
              Faça upload de um áudio ou vídeo para transcrição
            </p>
          </div>

          {/* Success message */}
          {uploadSuccess ? (
            <div className="card p-8 md:p-12 text-center animate-slide-in-up">
              <div className="w-20 h-20 mx-auto mb-6 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center">
                <svg className="w-10 h-10 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>

              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-3">
                ✅ Upload realizado com sucesso!
              </h2>

              <p className="text-slate-600 dark:text-slate-400 mb-6">
                Seu arquivo foi enfileirado para processamento.
                <br />
                ID do Job: <code className="text-sm bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">{jobId}</code>
              </p>

              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={() => router.push('/dashboard')}
                  className="btn-primary btn-md"
                >
                  Ver no Dashboard
                </button>
                <button
                  onClick={() => {
                    setUploadSuccess(false)
                    setJobId('')
                  }}
                  className="btn-secondary btn-md"
                >
                  Fazer Novo Upload
                </button>
              </div>

              <p className="text-sm text-slate-500 dark:text-slate-400 mt-6">
                Redirecionando para o dashboard em 3 segundos...
              </p>
            </div>
          ) : (
            /* Upload zone */
            <div className="space-y-6">
              <UploadZone onUploadComplete={handleUploadComplete} />

              {/* Info cards */}
              <div className="grid md:grid-cols-3 gap-4">
                <div className="card p-4">
                  <div className="text-2xl mb-2">⚡</div>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    Rápido
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Processamento em minutos
                  </p>
                </div>

                <div className="card p-4">
                  <div className="text-2xl mb-2">🎯</div>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    Preciso
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    IA treinada em português
                  </p>
                </div>

                <div className="card p-4">
                  <div className="text-2xl mb-2">🔒</div>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    Seguro
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Seus dados protegidos
                  </p>
                </div>
              </div>

              {/* Tips */}
              <div className="card p-6">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">
                  💡 Dicas para melhores resultados
                </h3>
                <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 dark:text-green-400 flex-shrink-0">✓</span>
                    <span>Use áudios com boa qualidade (sem muito ruído de fundo)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 dark:text-green-400 flex-shrink-0">✓</span>
                    <span>Fale claramente e em ritmo moderado</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 dark:text-green-400 flex-shrink-0">✓</span>
                    <span>Para vídeos, o áudio será extraído automaticamente</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 dark:text-green-400 flex-shrink-0">✓</span>
                    <span>O processamento pode levar de 2 a 10 minutos</span>
                  </li>
                </ul>
              </div>

              {/* Limits info */}
              <div className="text-center text-sm text-slate-500 dark:text-slate-400">
                <p>Limite: 3 uploads por hora • Tamanho máximo: 500MB</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
