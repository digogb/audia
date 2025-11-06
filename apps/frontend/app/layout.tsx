import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Audia - Transcrição com IA',
  description: 'Transcreva áudios e vídeos com diarização, chat inteligente e resumos automáticos',
  manifest: '/manifest.json',
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#3b82f6',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR" className="h-full">
      <head>
        <link rel="icon" href="/favicon.ico" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </head>
      <body className="h-full antialiased">
        {children}
      </body>
    </html>
  )
}
