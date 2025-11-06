'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { login, register } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const [isLogin, setIsLogin] = useState(true)
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    e.stopPropagation()

    setError('')
    setLoading(true)

    console.log('🔐 Iniciando autenticação...', { isLogin, email: formData.email })

    try {
      if (isLogin) {
        console.log('🔑 Fazendo login...')
        const user = await login(formData.email, formData.password)
        console.log('✅ Login bem-sucedido!', user)
      } else {
        console.log('📝 Fazendo registro...')
        if (formData.username.length < 3) {
          throw new Error('Username deve ter no mínimo 3 caracteres')
        }
        if (formData.password.length < 8) {
          throw new Error('Senha deve ter no mínimo 8 caracteres')
        }
        const user = await register(formData.email, formData.username, formData.password)
        console.log('✅ Registro bem-sucedido!', user)
      }
      console.log('🚀 Redirecionando para dashboard...')

      // Aguardar um pouco antes de redirecionar
      await new Promise(resolve => setTimeout(resolve, 500))
      router.push('/dashboard')
    } catch (err: any) {
      console.error('❌ Erro na autenticação:', err)
      const message = err.response?.data?.detail || err.message || 'Erro ao autenticar'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Left side - Branding (hidden on mobile) */}
      <div className="hidden md:flex md:w-1/2 gradient-primary p-12 flex-col justify-between text-white">
        <div>
          <h1 className="text-4xl font-bold mb-2">🎙️ Audia</h1>
          <p className="text-blue-100">Transcrição Inteligente com IA</p>
        </div>

        <div className="space-y-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">🎯</span>
            </div>
            <div>
              <h3 className="font-semibold mb-1">Transcrição com Diarização</h3>
              <p className="text-sm text-blue-100">
                Identifique automaticamente diferentes speakers no áudio
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">💬</span>
            </div>
            <div>
              <h3 className="font-semibold mb-1">Chat Inteligente</h3>
              <p className="text-sm text-blue-100">
                Faça perguntas sobre o conteúdo transcrito
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">📝</span>
            </div>
            <div>
              <h3 className="font-semibold mb-1">Resumos Automáticos</h3>
              <p className="text-sm text-blue-100">
                IA gera resumos concisos das transcrições
              </p>
            </div>
          </div>
        </div>

        <div className="text-sm text-blue-100">
          Powered by Azure AI • Oracle Cloud
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 bg-gradient-to-br from-blue-50 via-white to-violet-50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800">
        <div className="w-full max-w-md animate-slide-in-up">
          {/* Mobile logo */}
          <div className="md:hidden text-center mb-8">
            <h1 className="text-3xl font-bold text-gradient mb-2">🎙️ Audia</h1>
            <p className="text-slate-600 dark:text-slate-400">Transcrição Inteligente</p>
          </div>

          <div className="card p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl md:text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                {isLogin ? 'Bem-vindo de volta' : 'Criar conta'}
              </h2>
              <p className="text-slate-600 dark:text-slate-400">
                {isLogin
                  ? 'Entre para continuar usando o Audia'
                  : 'Comece a transcrever seus áudios agora'}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  placeholder="seu@email.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="input"
                  required
                  autoComplete="email"
                />
              </div>

              {!isLogin && (
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Username
                  </label>
                  <input
                    id="username"
                    type="text"
                    placeholder="seunome"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="input"
                    required={!isLogin}
                    minLength={3}
                    autoComplete="username"
                  />
                  <p className="text-xs text-slate-500 mt-1">Mínimo 3 caracteres</p>
                </div>
              )}

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Senha
                </label>
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="input"
                  required
                  minLength={8}
                  autoComplete={isLogin ? 'current-password' : 'new-password'}
                />
                <p className="text-xs text-slate-500 mt-1">Mínimo 8 caracteres</p>
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 animate-slide-in-down">
                  <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary btn-lg w-full"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="spinner w-4 h-4"></span>
                    Aguarde...
                  </span>
                ) : (
                  isLogin ? 'Entrar' : 'Criar conta'
                )}
              </button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => {
                  setIsLogin(!isLogin)
                  setError('')
                }}
                className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
              >
                {isLogin ? 'Não tem conta? Criar agora' : 'Já tem conta? Fazer login'}
              </button>
            </div>
          </div>

          {/* Features (mobile only) */}
          <div className="md:hidden mt-8 space-y-4">
            <div className="flex items-center gap-3 text-sm">
              <span className="text-xl">🎯</span>
              <span className="text-slate-600 dark:text-slate-400">Transcrição com Diarização</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-xl">💬</span>
              <span className="text-slate-600 dark:text-slate-400">Chat Inteligente</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-xl">📝</span>
              <span className="text-slate-600 dark:text-slate-400">Resumos Automáticos</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
