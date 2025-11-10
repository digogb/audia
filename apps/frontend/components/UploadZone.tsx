'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import api from '@/lib/api-client'

interface UploadZoneProps {
  onUploadComplete?: (data: any) => void
}

export default function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    setProgress(0)
    setError('')

    try {
      const response = await api.upload.file(file, (p) => setProgress(p))
      onUploadComplete?.(response.data)
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Erro ao fazer upload'
      setError(message)
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }, [onUploadComplete])

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: {
      'audio/mpeg': ['.mp3'],
      'audio/wav': ['.wav'],
      'audio/mp4': ['.m4a'],
      'audio/aac': ['.aac'],
      'audio/ogg': ['.ogg'],
      'video/mp4': ['.mp4'],
      'video/quicktime': ['.mov'],
      'video/x-msvideo': ['.avi'],
      'video/webm': ['.webm'],
    },
    maxSize: 500 * 1024 * 1024, // 500MB
    maxFiles: 1,
    disabled: uploading,
    validator: (file) => {
      // Validação adicional por extensão (fallback se MIME type falhar)
      const ext = file.name.toLowerCase().split('.').pop()
      const allowedExts = ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'mp4', 'mov', 'avi', 'webm']
      if (!ext || !allowedExts.includes(ext)) {
        return {
          code: 'invalid-extension',
          message: `Extensão .${ext} não permitida. Use: ${allowedExts.join(', ')}`
        }
      }
      return null
    },
  })

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-xl p-8 md:p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 scale-[1.02]'
            : 'border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-600'
          }
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>

            <div>
              <p className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                Enviando... {progress}%
              </p>
              <div className="w-full max-w-xs mx-auto bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-blue-600 h-full transition-all duration-300 rounded-full"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-16 h-16 mx-auto bg-gradient-to-br from-blue-500 to-violet-500 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>

            <div>
              <p className="text-lg md:text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
                {isDragActive ? '✨ Solte o arquivo aqui' : '📎 Arraste um arquivo ou clique'}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Áudio: MP3, WAV, M4A, AAC, OGG
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Vídeo: MP4, MOV, AVI, WEBM
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-500 mt-2">
                Tamanho máximo: 500MB
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Errors */}
      {error && (
        <div className="mt-4 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 animate-slide-in-down">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {fileRejections.length > 0 && (
        <div className="mt-4 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <p className="text-sm text-amber-800 dark:text-amber-200 font-medium mb-2">
            Arquivo rejeitado:
          </p>
          <ul className="text-xs text-amber-700 dark:text-amber-300 space-y-1">
            {fileRejections[0].errors.map((err) => (
              <li key={err.code}>• {err.message}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
