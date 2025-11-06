'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { logout, getCurrentUser, User } from '@/lib/auth'

export default function Navbar() {
  const router = useRouter()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    setUser(getCurrentUser())
  }, [])

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <nav className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="container-custom">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <button
            onClick={() => router.push('/dashboard')}
            className="flex items-center gap-2 text-xl font-bold text-slate-900 dark:text-slate-100 hover:opacity-80 transition-opacity"
          >
            <span className="text-2xl">🎙️</span>
            <span className="hidden sm:inline">Audia</span>
          </button>

          {/* Desktop navigation */}
          <div className="hidden md:flex items-center gap-4">
            <button
              onClick={() => router.push('/dashboard')}
              className="btn-ghost btn-sm"
            >
              📊 Dashboard
            </button>
            <button
              onClick={() => router.push('/upload')}
              className="btn-primary btn-sm"
            >
              ➕ Novo Upload
            </button>
          </div>

          {/* User menu */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {user?.username || 'Usuário'}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {user?.email}
              </p>
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="md:hidden btn-ghost btn-sm"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {isMenuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>

            {/* Desktop logout */}
            <button
              onClick={handleLogout}
              className="hidden md:block btn-ghost btn-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              Sair
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-slate-200 dark:border-slate-700 animate-slide-in-down">
            <div className="space-y-2">
              <button
                onClick={() => {
                  router.push('/dashboard')
                  setIsMenuOpen(false)
                }}
                className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
              >
                📊 Dashboard
              </button>
              <button
                onClick={() => {
                  router.push('/upload')
                  setIsMenuOpen(false)
                }}
                className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
              >
                ➕ Novo Upload
              </button>
              <div className="border-t border-slate-200 dark:border-slate-700 my-2"></div>
              <div className="px-4 py-2">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {user?.username}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {user?.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
              >
                Sair
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
