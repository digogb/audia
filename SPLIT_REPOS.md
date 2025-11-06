# 🔀 Guia para Separar em Repositórios Independentes

## Por que separar?

✅ **Escalabilidade** - Times diferentes podem trabalhar independentemente
✅ **CI/CD mais rápido** - Só testa/deploya o que mudou
✅ **Versionamento independente** - Backend v2.0, Frontend v1.5
✅ **Deploy independente** - Hotfix no backend sem tocar frontend
✅ **Permissões** - Controle de acesso granular por repo

---

## 🎯 Estratégia Recomendada

### **3 Repositórios:**

1. **`audia-backend`** - FastAPI puro
2. **`audia-frontend`** - Next.js puro
3. **`audia-infra`** - Docker, Nginx, scripts (opcional)

---

## 📋 Passo a Passo

### 1. Criar repositório do Backend

```bash
# Criar novo diretório
mkdir -p ~/audia-backend
cd ~/audia-backend

# Copiar apenas backend
cp -r ~/personal/audia/apps/backend/* .
cp ~/personal/audia/.env.example .
cp ~/personal/audia/Makefile .  # Adaptar depois

# Criar README específico
cat > README.md << 'EOF'
# Audia Backend

API FastAPI para transcrição de áudio/vídeo com Azure AI.

## Stack
- FastAPI
- Celery + Redis
- Azure Speech + OpenAI
- OCI Object Storage
- FAISS

## Quickstart

\`\`\`bash
cp .env.example .env
nano .env  # Configurar credenciais

# Com Docker
docker-compose up

# Ou local
pip install -r requirements.txt
uvicorn app.main:app --reload
\`\`\`

## API Docs
http://localhost:8000/docs

## Endpoints
- POST /v1/auth/register
- POST /v1/auth/login
- POST /v1/upload
- GET /v1/jobs/{id}/status
- GET /v1/transcriptions/{id}
- POST /v1/chat/{id}
- POST /v1/summary/{id}
EOF

# Git init
git init
git add .
git commit -m "Initial commit: Audia Backend"

# Criar no GitHub e push
gh repo create audia-backend --public --source=. --remote=origin
git push -u origin main
```

### 2. Criar repositório do Frontend

```bash
# Criar novo diretório
mkdir -p ~/audia-frontend
cd ~/audia-frontend

# Copiar apenas frontend
cp -r ~/personal/audia/apps/frontend/* .

# Criar README específico
cat > README.md << 'EOF'
# Audia Frontend

Interface web Next.js para o sistema Audia.

## Stack
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Axios

## Quickstart

\`\`\`bash
npm install
npm run dev
\`\`\`

Acesse: http://localhost:3000

## Variáveis de Ambiente

\`\`\`bash
NEXT_PUBLIC_API_URL=http://localhost:8000
\`\`\`

## Build

\`\`\`bash
npm run build
npm start
\`\`\`
EOF

# .env.example específico do frontend
cat > .env.example << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

# Git init
git init
git add .
git commit -m "Initial commit: Audia Frontend"

# Criar no GitHub e push
gh repo create audia-frontend --public --source=. --remote=origin
git push -u origin main
```

### 3. Criar repositório de Infraestrutura (Opcional)

```bash
mkdir -p ~/audia-infra
cd ~/audia-infra

# Copiar configs de infra
cp -r ~/personal/audia/deploy/* .
cp ~/personal/audia/.env.example .

# Criar README
cat > README.md << 'EOF'
# Audia Infrastructure

Configurações de deploy e infraestrutura.

## Conteúdo
- Docker Compose (desenvolvimento)
- Nginx (produção)
- Scripts de deploy OCI
- GitHub Actions (CI/CD)

## Uso

\`\`\`bash
# Desenvolvimento local
docker-compose up

# Deploy produção
./scripts/deploy-vm1.sh  # Frontend
./scripts/deploy-vm2.sh  # Backend
\`\`\`
EOF

git init
git add .
git commit -m "Initial commit: Audia Infrastructure"

gh repo create audia-infra --public --source=. --remote=origin
git push -u origin main
```

---

## 🔄 Ajustes Necessários Após Separação

### Backend (audia-backend)

**1. Criar `docker-compose.yml` próprio:**

```yaml
# docker-compose.yml (na raiz do repo backend)
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  worker:
    build: .
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
    command: celery -A celery_app worker --loglevel=info

volumes:
  redis_data:
```

**2. Criar `Makefile` específico:**

```makefile
.PHONY: dev test lint

dev:
	docker-compose up --build

test:
	pytest -v --cov=app

lint:
	ruff check app/
	mypy app/

clean:
	docker-compose down -v
```

**3. GitHub Actions (`audia-backend/.github/workflows/ci.yml`):**

```yaml
name: Backend CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest -v --cov=app
      - run: ruff check app/

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to VM2
        run: |
          # SSH e deploy apenas do backend
          ssh ${{ secrets.VM2_HOST }} "cd ~/backend && git pull && docker-compose up -d --build"
```

### Frontend (audia-frontend)

**1. GitHub Actions (`audia-frontend/.github/workflows/ci.yml`):**

```yaml
name: Frontend CI/CD

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - name: Deploy to VM1
        run: |
          rsync -avz out/ ${{ secrets.VM1_HOST }}:/var/www/audia/
```

**2. Configurar URL da API:**

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.audia.com
```

---

## 🎯 Vantagens da Separação

### Desenvolvimento
```bash
# Time Backend trabalha aqui
cd ~/audia-backend
git checkout feature/new-endpoint
# Commits não afetam frontend

# Time Frontend trabalha aqui
cd ~/audia-frontend
git checkout feature/new-ui
# Commits não afetam backend
```

### CI/CD Independente
```bash
# Push no backend → só testa/deploya backend (2 min)
# Push no frontend → só testa/deploya frontend (1 min)

# Antes (monorepo): sempre testava tudo (5 min)
```

### Versionamento Semântico
```bash
# Backend
v1.0.0 → v2.0.0 (breaking change na API)

# Frontend
v1.5.0 → v1.5.1 (hotfix no UI)

# Podem evoluir independentemente!
```

---

## ⚠️ Desvantagens da Separação

❌ **Sincronização manual** - Mudanças na API precisam ser refletidas no frontend
❌ **Mais repos para gerenciar** - 3 PRs em vez de 1
❌ **Contratos de API** - Precisa de versionamento rigoroso
❌ **Setup inicial mais complexo** - Dev novo precisa clonar 2-3 repos

---

## 💡 Solução Híbrida (Melhor dos 2 Mundos)

### **Opção: Monorepo com Workspaces**

```bash
audia/  # Um único repo
├── packages/
│   ├── backend/     # Workspace independente
│   ├── frontend/    # Workspace independente
│   └── shared/      # Tipos TypeScript compartilhados!
├── .github/
│   └── workflows/
│       ├── backend.yml   # Só roda se mudar backend/
│       └── frontend.yml  # Só roda se mudar frontend/
└── package.json  # Root workspace
```

**Vantagens:**
- ✅ Um repo só (fácil de começar)
- ✅ CI/CD condicional (rápido)
- ✅ Pode compartilhar tipos TypeScript
- ✅ Versionamento unificado quando necessário

**Como fazer:**
```bash
# package.json raiz
{
  "workspaces": ["packages/*"],
  "scripts": {
    "dev:backend": "npm run dev --workspace=backend",
    "dev:frontend": "npm run dev --workspace=frontend"
  }
}
```

---

## 🎯 Minha Recomendação

### **Para MVP/Startup (você agora):**
👉 **Mantenha o monorepo** mas organize melhor:
- Adicione CI/CD condicional (só testa o que mudou)
- Use workspaces do npm
- Documente bem a separação lógica

### **Para Produção/Escala (futuro):**
👉 **Separe em 2-3 repos** quando:
- Tiver mais de 2 devs trabalhando
- Backend e frontend evoluírem independentemente
- Precisar de deploys independentes frequentes

---

## 📝 Decisão Rápida

**Mantenha monorepo SE:**
- Você é dev solo ou time pequeno (1-3 pessoas)
- Backend e frontend sempre mudam juntos
- Simplicidade > escalabilidade (agora)

**Separe repos SE:**
- Time de 4+ pessoas
- Backend tem API pública usada por outros clientes
- Frontend pode usar múltiplos backends
- Quer deploys totalmente independentes

---

## 🚀 Ação Imediata

**Minha sugestão para você AGORA:**

1. ✅ **Mantenha o monorepo** (já está pronto)
2. ✅ **Complete o frontend** primeiro (funcional é prioridade)
3. ✅ **Teste o fluxo completo**
4. ⏳ **Depois** decida separar baseado em:
   - Quantas pessoas vão trabalhar?
   - Com que frequência backend e frontend mudam separadamente?

**Você sempre pode separar depois!** É mais fácil:
- Monorepo → Repos separados ✅
- Do que: Repos separados → Monorepo ❌

---

Quer que eu crie scripts para facilitar a separação quando decidir fazer? Ou prefere ajustes no monorepo atual para organizá-lo melhor?
