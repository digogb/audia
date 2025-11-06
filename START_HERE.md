# 🚀 START HERE - Audia

## Início Rápido em 3 Passos

### ⚠️ Importante: Chaves Azure e OCI

**O backend precisa de credenciais Azure e OCI para funcionar completamente.**

Se você **não tem** as credenciais agora:
- ✅ O backend vai subir normalmente
- ✅ O frontend vai funcionar (login, dashboard, upload)
- ❌ A transcrição **não vai funcionar** (precisa Azure Speech)
- ❌ O chat **não vai funcionar** (precisa Azure OpenAI)

---

## Passo 1: Configurar Credenciais (Opcional para teste)

```bash
# Editar arquivo .env
nano .env

# Adicionar suas chaves (se tiver):
AZURE_SPEECH_KEY=sua_chave_aqui
AZURE_SPEECH_REGION=brazilsouth
AZURE_OPENAI_KEY=sua_chave_aqui
AZURE_OPENAI_ENDPOINT=https://sua-instancia.openai.azure.com/

# OCI (se tiver):
OCI_NAMESPACE=seu_namespace
OCI_COMPARTMENT_OCID=ocid1.compartment.oc1..xxxxx
```

**Não tem credenciais?** Tudo bem! Continue sem elas para testar a interface.

---

## Passo 2: Subir o Backend

```bash
# Na raiz do projeto
make dev
```

Aguarde até ver:
```
✅ audia-backend  | Application startup complete
✅ audia-worker   | ready
✅ audia-redis    | Ready to accept connections
```

**Teste:** http://localhost:8000/health

Deve retornar: `{"status":"healthy","version":"1.0.0","app":"Audia"}`

---

## Passo 3: Subir o Frontend

```bash
# Em OUTRO terminal
cd apps/frontend

# Instalar dependências (só na primeira vez)
npm install

# Rodar em desenvolvimento
npm run dev
```

Aguarde até ver:
```
✓ Ready in 2.3s
○ Local: http://localhost:3000
```

---

## ✅ Testar Tudo

### 1. Acessar o App

Abra: **http://localhost:3000**

### 2. Criar Conta

```
Email: teste@exemplo.com
Username: teste
Senha: senha12345
```

### 3. Explorar Interface

- ✅ Dashboard vazio (sem transcrições ainda)
- ✅ Página de Upload
- ✅ Navegação mobile

### 4. Testar Upload (sem processar)

- Arraste um arquivo MP3
- Verá mensagem de sucesso
- Job aparecerá no dashboard como "QUEUED"
- **Vai ficar parado** (normal sem credenciais Azure)

---

## 🔧 Se algo der errado

### Backend não sobe

```bash
# Ver logs
make logs

# Erro comum: porta 8000 ocupada
lsof -i :8000
# Se aparecer algo, matar o processo

# Limpar e reiniciar
make clean
make dev
```

### Frontend não sobe

```bash
# Limpar cache
cd apps/frontend
rm -rf .next node_modules
npm install
npm run dev
```

### Erro "Module not found"

```bash
# Criar __init__.py faltantes
cd ~/personal/audia
find apps/backend/app -type d -exec touch {}/__init__.py \;
```

---

## 📚 Próximos Passos

### Se tiver credenciais Azure

1. Adicionar no `.env`:
   - `AZURE_SPEECH_KEY`
   - `AZURE_OPENAI_KEY`

2. Reiniciar backend:
```bash
make stop
make dev
```

3. Fazer upload de um áudio real

4. Aguardar processamento (5-10 min)

5. Ver transcrição + chat funcionando!

### Se NÃO tiver credenciais

**Opção 1:** Continuar explorando a interface (já está completa!)

**Opção 2:** Criar conta grátis Azure:
- [Azure Free Trial](https://azure.microsoft.com/free/)
- Criar recurso Speech Service
- Criar recurso OpenAI (precisa solicitar acesso)

**Opção 3:** Usar mock data (vamos criar):

```bash
# TODO: criar script para popular com dados fake
# Permitirá testar chat e visualização sem Azure
```

---

## 🎯 O que está funcionando AGORA

### ✅ Sem credenciais Azure/OCI

- ✅ Frontend 100% (todas as telas)
- ✅ Backend API (rotas funcionando)
- ✅ Login/Registro (JWT)
- ✅ Upload de arquivos
- ✅ Dashboard
- ✅ Banco de dados (SQLite)
- ❌ Processamento de transcrição (precisa Azure)
- ❌ Chat (precisa Azure OpenAI)

### ✅ Com credenciais Azure/OCI

- ✅ Tudo acima +
- ✅ Transcrição real com diarização
- ✅ Chat inteligente sobre o conteúdo
- ✅ Resumos automáticos
- ✅ Armazenamento em nuvem (OCI)

---

## 📖 Documentação

- **[README.md](README.md)** - Documentação completa
- **[QUICKSTART.md](QUICKSTART.md)** - Guia rápido de 5 min
- **[FRONTEND_COMPLETE.md](FRONTEND_COMPLETE.md)** - Guia do frontend
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Resumo do projeto

---

## 🆘 Ajuda

### Comandos úteis

```bash
# Ver logs do backend
make logs-backend

# Ver logs do worker
make logs-worker

# Parar tudo
make stop

# Limpar tudo e recomeçar
make clean
make dev

# Health check
curl http://localhost:8000/health

# Ver containers rodando
docker ps
```

### Portas usadas

- **3000** - Frontend (Next.js)
- **8000** - Backend (FastAPI)
- **6379** - Redis
- **5555** - Flower (monitor Celery, opcional)

### Ainda com problemas?

1. Verifique se Docker está rodando:
```bash
docker ps
```

2. Verifique se as portas estão livres:
```bash
lsof -i :3000
lsof -i :8000
lsof -i :6379
```

3. Veja os logs completos:
```bash
make logs
```

---

## 🎉 Tudo Funcionando?

**Parabéns!** Você tem:

- ✅ Backend FastAPI rodando
- ✅ Frontend Next.js moderno
- ✅ Interface completa e responsiva
- ✅ Sistema pronto para adicionar credenciais Azure

**Próximo passo:** Adicione credenciais Azure para ativar IA! 🚀

---

*Projeto Audia - Transcrição Inteligente com IA*
