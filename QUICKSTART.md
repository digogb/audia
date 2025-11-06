# 🚀 Audia - Quickstart

## Start em 5 Minutos

### 1. Copie as credenciais

```bash
cp .env.example .env
nano .env
```

Edite apenas estas linhas essenciais:
```bash
AZURE_SPEECH_KEY=sua_chave_aqui
AZURE_SPEECH_REGION=brazilsouth
AZURE_OPENAI_KEY=sua_chave_aqui
AZURE_OPENAI_ENDPOINT=https://sua-instancia.openai.azure.com/
OCI_NAMESPACE=seu_namespace
OCI_COMPARTMENT_OCID=ocid1.compartment.oc1..xxxxx
JWT_SECRET_KEY=gere_uma_chave_segura_de_32_caracteres_minimo
```

### 2. Suba o backend

```bash
make dev
```

Aguarde até ver:
```
✅ backend  | Application startup complete
✅ worker   | celery@... ready
✅ redis    | Ready to accept connections
```

### 3. Teste a API

```bash
# Health check
curl http://localhost:8000/health

# Resposta esperada:
# {"status":"healthy","version":"1.0.0","app":"Audia"}
```

### 4. Acesse a documentação

Abra no navegador: **http://localhost:8000/docs**

### 5. Teste um upload

```bash
# 1. Registre um usuário
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@exemplo.com",
    "username": "teste",
    "password": "senha123456"
  }'

# Copie o access_token da resposta

# 2. Faça upload de um áudio
curl -X POST http://localhost:8000/v1/upload \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN_AQUI" \
  -F "file=@seu_audio.mp3"

# Copie o job_id da resposta

# 3. Verifique o status
curl -X GET http://localhost:8000/v1/jobs/SEU_JOB_ID/status \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN_AQUI"
```

---

## 🎯 Comandos Úteis

```bash
# Ver logs em tempo real
make logs

# Parar tudo
make stop

# Resetar banco de dados
make db-reset

# Limpar tudo
make clean
```

---

## 📝 Próximos Passos

1. ✅ Backend rodando? → Continue para [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
2. ✅ Frontend completo? → Configure Azure e OCI
3. ✅ Tudo testado? → Deploy: `make deploy-all`

---

## ❌ Problemas Comuns

### Backend não inicia
```bash
# Verificar portas em uso
lsof -i :8000
lsof -i :6379

# Limpar e reiniciar
make clean
make dev
```

### Erro "OCI config not found"
```bash
# Criar config OCI
mkdir -p ~/.oci
nano ~/.oci/config

# Conteúdo mínimo:
[DEFAULT]
user=ocid1.user.oc1..xxxxx
fingerprint=xx:xx:xx:...
tenancy=ocid1.tenancy.oc1..xxxxx
region=sa-saopaulo-1
key_file=~/.oci/key.pem
```

### Erro no Celery worker
```bash
# Ver logs detalhados
make logs-worker

# Comum: falta de credenciais Azure/OCI
# Solução: verificar .env
```

---

## 🎓 Documentação Completa

- [README.md](README.md) - Documentação principal
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Resumo do que foi criado
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Como completar frontend

---

**Boa sorte! 🚀**
