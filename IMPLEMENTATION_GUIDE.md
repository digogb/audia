# Guia de Implementação Completo - Projeto Audia

## ✅ O que foi criado

### Backend (100% Completo)
- ✅ **FastAPI** com estrutura completa
- ✅ **Serviços Azure** (Speech Batch API + OpenAI)
- ✅ **Serviço OCI** Object Storage
- ✅ **Sistema FAISS** para embeddings e RAG
- ✅ **Celery** com tasks assíncronas
- ✅ **Autenticação JWT** com refresh tokens
- ✅ **Todas as rotas** (auth, upload, jobs, transcriptions, chat, summary)
- ✅ **Modelos Pydantic** completos
- ✅ **Dockerfile** otimizado multi-stage
- ✅ **Docker Compose** configurado

### Infraestrutura (100% Completo)
- ✅ **Nginx** com SSL, rate limiting, proxy reverso
- ✅ **Scripts de deploy** para OCI VMs
- ✅ **GitHub Actions** CI/CD pipeline completo
- ✅ **Makefile** com comandos úteis
- ✅ **Documentação** completa no README

### Frontend (70% Completo - Arquivos Essenciais)
- ✅ **Configurações** (package.json, tsconfig, next.config, tailwind)
- ✅ **Cliente API** com refresh automático de tokens
- ✅ **Auth utilities** (login, register, logout)
- ⚠️ **Páginas** (precisam ser criadas)
- ⚠️ **Componentes** (precisam ser criados)

## 📝 Arquivos Frontend que faltam criar

### 1. Layout Principal e Home

**`apps/frontend/app/layout.tsx`**:
```typescript
import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Audia - Transcrição com IA',
  description: 'Transcreva áudios e vídeos com diarização e chat inteligente',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  )
}
```

**`apps/frontend/app/page.tsx`**:
```typescript
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    if (isAuthenticated()) {
      router.push('/dashboard')
    } else {
      router.push('/login')
    }
  }, [router])

  return <div>Carregando...</div>
}
```

### 2. Página de Login

**`apps/frontend/app/login/page.tsx`**:
```typescript
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
    setError('')
    setLoading(true)

    try {
      if (isLogin) {
        await login(formData.email, formData.password)
      } else {
        await register(formData.email, formData.username, formData.password)
      }
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao autenticar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <h2 className="text-3xl font-bold text-center">
          {isLogin ? 'Login' : 'Registrar'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full px-4 py-2 border rounded"
            required
          />

          {!isLogin && (
            <input
              type="text"
              placeholder="Username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="w-full px-4 py-2 border rounded"
              required
            />
          )}

          <input
            type="password"
            placeholder="Senha"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            className="w-full px-4 py-2 border rounded"
            required
          />

          {error && <div className="text-red-500 text-sm">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Aguarde...' : isLogin ? 'Entrar' : 'Registrar'}
          </button>
        </form>

        <button
          onClick={() => setIsLogin(!isLogin)}
          className="w-full text-sm text-blue-600 hover:underline"
        >
          {isLogin ? 'Criar conta' : 'Já tenho conta'}
        </button>
      </div>
    </div>
  )
}
```

### 3. Componente de Upload

**`apps/frontend/components/UploadZone.tsx`**:
```typescript
'use client'
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import api from '@/lib/api-client'

export default function UploadZone({ onUploadComplete }: any) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    setProgress(0)

    try {
      const response = await api.upload.file(file, (p) => setProgress(p))
      onUploadComplete?.(response.data)
    } catch (error) {
      console.error('Upload error:', error)
    } finally {
      setUploading(false)
    }
  }, [onUploadComplete])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a'],
      'video/*': ['.mp4', '.mov', '.avi'],
    },
    maxSize: 500 * 1024 * 1024, // 500MB
    disabled: uploading,
  })

  return (
    <div
      {...getRootProps()}
      className={\`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors \${
        isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
      } \${uploading ? 'opacity-50 cursor-not-allowed' : ''}\`}
    >
      <input {...getInputProps()} />

      {uploading ? (
        <div>
          <p className="text-lg font-semibold mb-2">Enviando... {progress}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: \`\${progress}%\` }}
            />
          </div>
        </div>
      ) : (
        <div>
          <p className="text-lg font-semibold mb-2">
            {isDragActive ? 'Solte o arquivo aqui' : 'Arraste um arquivo ou clique'}
          </p>
          <p className="text-sm text-gray-500">
            Suporta: MP3, WAV, MP4, MOV (máx. 500MB)
          </p>
        </div>
      )}
    </div>
  )
}
```

### 4. Componente de Chat

**`apps/frontend/components/Chat.tsx`**:
```typescript
'use client'
import { useState } from 'react'
import api from '@/lib/api-client'

export default function Chat({ jobId }: { jobId: string }) {
  const [messages, setMessages] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await api.chat.send(jobId, {
        question: input,
        chat_history: messages,
      })

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={\`p-3 rounded-lg \${
              msg.role === 'user'
                ? 'bg-blue-100 ml-auto max-w-[80%]'
                : 'bg-gray-100 mr-auto max-w-[80%]'
            }\`}
          >
            <p className="text-sm">{msg.content}</p>
          </div>
        ))}
      </div>

      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Faça uma pergunta sobre a transcrição..."
            className="flex-1 px-4 py-2 border rounded"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '...' : 'Enviar'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

### 5. Adicionar CSS Global

**`apps/frontend/app/globals.css`**:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
```

### 6. Dockerfile do Frontend

**`apps/frontend/Dockerfile`**:
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV production

COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
```

## 🚀 Como iniciar o projeto

### 1. Configuração Inicial

```bash
# Clonar e entrar no projeto
cd audia

# Copiar e editar .env
cp .env.example .env
nano .env  # Adicionar suas chaves Azure e OCI

# Instalar dependências
make setup
```

### 2. Desenvolvimento Local

```bash
# Iniciar stack completa (backend + worker + redis)
make dev

# Em outro terminal, iniciar frontend
make dev-frontend

# Acessar:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Docs API: http://localhost:8000/docs
```

### 3. Deploy em Produção

```bash
# 1. Configurar OCI
make init-oci

# 2. Criar VMs via Console OCI
# 3. Adicionar IPs como secrets no GitHub

# 4. Deploy manual
make deploy-vm2  # Backend
make deploy-vm1  # Frontend

# Ou via CI/CD: push para branch main
```

## 📋 Checklist de Conclusão

### Backend
- [x] FastAPI configurado
- [x] Todas as rotas implementadas
- [x] Serviços Azure integrados
- [x] OCI Object Storage integrado
- [x] FAISS para embeddings
- [x] Celery workers
- [x] JWT auth
- [x] Docker e docker-compose

### Frontend (Completar)
- [x] Configurações Next.js
- [x] Cliente API
- [x] Auth utilities
- [ ] Criar `app/layout.tsx`
- [ ] Criar `app/page.tsx`
- [ ] Criar `app/login/page.tsx`
- [ ] Criar `app/dashboard/page.tsx`
- [ ] Criar `app/upload/page.tsx`
- [ ] Criar `app/transcription/[jobId]/page.tsx`
- [ ] Criar `components/UploadZone.tsx`
- [ ] Criar `components/Chat.tsx`
- [ ] Criar `components/TranscriptionViewer.tsx`
- [ ] Criar `app/globals.css`
- [ ] Criar `Dockerfile`

### Infraestrutura
- [x] Nginx configurado
- [x] Scripts de deploy
- [x] GitHub Actions CI/CD
- [x] Makefile
- [x] Documentação

## 🎯 Próximos Passos

1. **Completar Frontend**: Criar os arquivos listados acima
2. **Testar Localmente**: `make dev` e testar fluxo completo
3. **Configurar Azure**: Criar recursos Speech e OpenAI
4. **Configurar OCI**: Criar bucket e VMs
5. **Deploy**: Executar `make deploy-all`
6. **Testar Produção**: Upload de áudio teste

## 📚 Recursos Adicionais

- [Docs FastAPI](https://fastapi.tiangolo.com/)
- [Docs Next.js](https://nextjs.org/docs)
- [Azure Speech SDK](https://learn.microsoft.com/azure/cognitive-services/speech-service/)
- [Azure OpenAI](https://learn.microsoft.com/azure/cognitive-services/openai/)
- [OCI SDK Python](https://docs.oracle.com/en-us/iaas/tools/python/latest/)

---

**Projeto gerado com Claude Code - Anthropic**
