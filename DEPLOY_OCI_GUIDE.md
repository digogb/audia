# Guia de Deploy - Audia na Oracle Cloud Infrastructure (OCI)

Este guia detalha como fazer o deploy completo do Audia usando VMs gratuitas da OCI e serviços de IA da Azure.

## Arquitetura

- **VM 1 (Backend)**: FastAPI + Celery + Redis
- **VM 2 (Frontend)**: Next.js
- **OCI Object Storage**: Arquivos de áudio e transcrições
- **Azure Services**: Speech-to-Text e OpenAI

---

## Parte 1: Configuração Inicial da OCI

### 1.1. Criar Conta OCI (se ainda não tiver)

1. Acesse: https://www.oracle.com/cloud/free/
2. Crie uma conta (Free Tier - sempre gratuito)
3. Anote seu **Tenancy Name** e **Region**

### 1.2. Criar Bucket no Object Storage

1. No console OCI, vá em **Storage** > **Buckets**
2. Clique em **Create Bucket**
3. Configurações:
   - **Name**: `audia-storage` (ou o nome que está no seu .env)
   - **Default Storage Tier**: Standard
   - **Encryption**: Encrypt using Oracle managed keys
   - **Emit Object Events**: Não marcar
4. Clique em **Create**
5. Anote:
   - **Namespace**: Aparece no topo da página
   - **Bucket Name**: audia-storage

### 1.3. Configurar API Key para acesso ao Object Storage

1. No console OCI, clique no ícone do usuário (canto superior direito)
2. Clique em **User Settings**
3. No menu lateral esquerdo, clique em **API Keys**
4. Clique em **Add API Key**
5. Selecione **Generate API Key Pair**
6. **IMPORTANTE**: Faça download de ambas as chaves:
   - Private Key (baixar e salvar como `~/.oci/oci_api_key.pem`)
   - Public Key (será adicionada automaticamente)
7. Copie o conteúdo da **Configuration File Preview** e salve em `~/.oci/config`

Exemplo de `~/.oci/config`:
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaa...
fingerprint=xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
tenancy=ocid1.tenancy.oc1..aaaaaaaa...
region=sa-saopaulo-1
key_file=~/.oci/oci_api_key.pem
```

### 1.4. Ajustar permissões da chave privada

```bash
mkdir -p ~/.oci
chmod 600 ~/.oci/oci_api_key.pem
chmod 600 ~/.oci/config
```

---

## Parte 2: Criar VMs no OCI

### 2.1. Criar VM para Backend

1. No console OCI, vá em **Compute** > **Instances**
2. Clique em **Create Instance**
3. Configurações:
   - **Name**: `audia-backend`
   - **Compartment**: Selecione seu compartment
   - **Availability Domain**: Qualquer um disponível
   - **Image**: `Ubuntu 22.04` (clique em "Change Image" se necessário)
   - **Shape**: `VM.Standard.E2.1.Micro` (Always Free)
   - **Virtual Cloud Network**: Selecione ou crie uma VCN
   - **Subnet**: Selecione uma subnet pública
   - **Assign a public IPv4 address**: Marcar
   - **SSH Keys**: Faça upload da sua chave pública SSH ou gere uma nova
4. Clique em **Create**
5. **Anote o IP público** quando a VM estiver rodando

### 2.2. Criar VM para Frontend

Repita o processo acima com:
- **Name**: `audia-frontend`
- Mesmas configurações de shape e image
- **Anote o IP público**

### 2.3. Configurar Security Lists (Firewall)

Para cada VM, configure as regras de entrada:

**VM Backend (audia-backend)**:
1. Vá em **Networking** > **Virtual Cloud Networks**
2. Clique na VCN que você criou
3. Clique em **Security Lists** > **Default Security List**
4. Clique em **Add Ingress Rules**
5. Adicione as seguintes regras:

| Source CIDR | Protocol | Source Port | Destination Port | Description |
|-------------|----------|-------------|------------------|-------------|
| 0.0.0.0/0   | TCP      | All         | 22               | SSH         |
| 0.0.0.0/0   | TCP      | All         | 8000             | FastAPI     |
| 0.0.0.0/0   | TCP      | All         | 6379             | Redis       |
| 0.0.0.0/0   | TCP      | All         | 5555             | Flower (opcional) |

**VM Frontend (audia-frontend)**:
| Source CIDR | Protocol | Source Port | Destination Port | Description |
|-------------|----------|-------------|------------------|-------------|
| 0.0.0.0/0   | TCP      | All         | 22               | SSH         |
| 0.0.0.0/0   | TCP      | All         | 80               | HTTP        |
| 0.0.0.0/0   | TCP      | All         | 443              | HTTPS       |
| 0.0.0.0/0   | TCP      | All         | 3000             | Next.js     |

---

## Parte 3: Preparar as VMs

### 3.1. Conectar via SSH às VMs

```bash
# Backend
ssh ubuntu@<IP_BACKEND>

# Frontend (em outro terminal)
ssh ubuntu@<IP_FRONTEND>
```

### 3.2. Instalar Docker em ambas as VMs

Execute em **cada VM**:

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Adicionar repositório Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Testar Docker
docker --version
docker compose version
```

### 3.3. Instalar ffmpeg na VM Backend

```bash
sudo apt install -y ffmpeg
ffmpeg -version
```

---

## Parte 4: Deploy do Backend

### 4.1. Copiar configuração OCI para a VM Backend

Na sua máquina local:

```bash
# Copiar configuração OCI
scp -r ~/.oci ubuntu@<IP_BACKEND>:~/

# Na VM backend, ajustar permissões
ssh ubuntu@<IP_BACKEND>
chmod 600 ~/.oci/oci_api_key.pem
chmod 600 ~/.oci/config
```

### 4.2. Clonar repositório na VM Backend

```bash
# Na VM backend
git clone https://github.com/digogb/audia.git
cd audia
```

### 4.3. Criar arquivo .env

```bash
nano .env
```

Cole o conteúdo do seu arquivo .env local (com as credenciais Azure e OCI). Exemplo:

```env
# Azure Speech Services
AZURE_SPEECH_KEY=sua_chave_azure_speech
AZURE_SPEECH_REGION=eastus

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://seu-recurso.openai.azure.com/
AZURE_OPENAI_API_KEY=sua_chave_openai
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# OCI Object Storage
OCI_NAMESPACE=seu_namespace
OCI_BUCKET=audia-storage
OCI_COMPARTMENT_OCID=ocid1.compartment.oc1..aaaaaaaa...
OCI_REGION=sa-saopaulo-1

# JWT
JWT_SECRET=gere_uma_chave_secreta_forte_aqui
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=10080

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Database
DATABASE_URL=sqlite:////app/data/audia.db
FAISS_PATH=/app/data/faiss_store

# Timezone
TZ=America/Sao_Paulo

# Backend URL (para CORS)
BACKEND_URL=http://<IP_BACKEND>:8000
FRONTEND_URL=http://<IP_FRONTEND>:3000
```

Salve com `Ctrl+X`, depois `Y`, depois `Enter`.

### 4.4. Iniciar os containers

```bash
cd deploy
docker compose up -d --build
```

### 4.5. Verificar logs

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f redis
```

### 4.6. Testar API

```bash
curl http://localhost:8000/health
# Deve retornar: {"status":"ok"}
```

Da sua máquina local:
```bash
curl http://<IP_BACKEND>:8000/health
```

---

## Parte 5: Deploy do Frontend

### 5.1. Clonar repositório na VM Frontend

```bash
# Na VM frontend
git clone https://github.com/digogb/audia.git
cd audia/apps/frontend
```

### 5.2. Criar arquivo .env.local

```bash
nano .env.local
```

Cole:
```env
NEXT_PUBLIC_API_URL=http://<IP_BACKEND>:8000/v1
```

### 5.3. Construir e rodar o frontend

**Opção A: Com Docker**

Criar `Dockerfile` na pasta `apps/frontend`:
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

Criar `docker-compose.yml`:
```yaml
services:
  frontend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://<IP_BACKEND>:8000/v1
    restart: unless-stopped
```

Rodar:
```bash
docker compose up -d --build
```

**Opção B: Com Node.js diretamente**

```bash
# Instalar Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Instalar dependências
npm ci

# Build
npm run build

# Rodar em produção com PM2
sudo npm install -g pm2
pm2 start npm --name "audia-frontend" -- start
pm2 startup
pm2 save
```

### 5.4. Testar Frontend

Da sua máquina local:
```bash
curl http://<IP_FRONTEND>:3000
```

Acesse no navegador: `http://<IP_FRONTEND>:3000`

---

## Parte 6: Configurar Domínio e HTTPS (Opcional)

### 6.1. Apontar domínio para os IPs

Configure DNS A records:
- `api.seudominio.com` → `<IP_BACKEND>`
- `app.seudominio.com` → `<IP_FRONTEND>`

### 6.2. Instalar Nginx e Certbot

**Na VM Frontend**:
```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# Configurar Nginx
sudo nano /etc/nginx/sites-available/audia
```

Cole:
```nginx
server {
    listen 80;
    server_name app.seudominio.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Ativar:
```bash
sudo ln -s /etc/nginx/sites-available/audia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Obter certificado SSL:
```bash
sudo certbot --nginx -d app.seudominio.com
```

**Repetir para Backend** com `api.seudominio.com` apontando para porta 8000.

---

## Parte 7: Monitoramento e Manutenção

### Verificar status dos containers

```bash
docker compose ps
docker compose logs -f
```

### Atualizar código

```bash
cd ~/audia
git pull
cd deploy
docker compose down
docker compose up -d --build
```

### Backup do banco de dados

```bash
# Copiar banco de dados da VM para local
scp ubuntu@<IP_BACKEND>:/var/lib/docker/volumes/deploy_backend_data/_data/audia.db ./backup_$(date +%Y%m%d).db
```

### Monitorar Celery com Flower

Acesse: `http://<IP_BACKEND>:5555`

Para rodar Flower:
```bash
cd deploy
docker compose --profile debug up -d flower
```

---

## Custos e Limites Free Tier

**Oracle Cloud - Always Free**:
- 2x VMs AMD (1 core, 1GB RAM cada)
- 20 GB Object Storage
- 10 TB/mês de saída de dados

**Azure**:
- Speech to Text: Até 5 horas/mês grátis, depois ~$1/hora
- OpenAI GPT-4: Cobrado por tokens (varia por uso)

**Dica**: Configure alertas de billing no Azure para não ter surpresas!

---

## Troubleshooting

### Erro: Cannot connect to Docker daemon
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

### Erro: OCI Object Storage access denied
- Verifique se `~/.oci/config` e `~/.oci/oci_api_key.pem` existem na VM
- Verifique permissões: `chmod 600 ~/.oci/*`
- Verifique se o compartment OCID está correto no .env

### Frontend não conecta com backend
- Verifique se `NEXT_PUBLIC_API_URL` está correto
- Verifique se a porta 8000 está aberta no Security List
- Teste: `curl http://<IP_BACKEND>:8000/health`

### Transcrição falha
- Verifique credenciais Azure no .env
- Verifique logs: `docker compose logs -f worker`
- Verifique se ffmpeg está instalado na VM

---

## Próximos Passos

1. ✅ Configurar OCI Object Storage
2. ✅ Criar VMs
3. ✅ Deploy Backend
4. ✅ Deploy Frontend
5. ⏳ Configurar domínio e HTTPS
6. ⏳ Configurar backup automático
7. ⏳ Configurar monitoramento (Uptime Robot, etc)

---

## Comandos Úteis

```bash
# Ver logs em tempo real
docker compose logs -f

# Reiniciar apenas um serviço
docker compose restart backend

# Ver uso de recursos
docker stats

# Limpar imagens antigas
docker system prune -a

# Acessar shell de um container
docker exec -it audia-backend bash
```

---

**Documentação criada em**: $(date)
**Repositório**: https://github.com/digogb/audia
