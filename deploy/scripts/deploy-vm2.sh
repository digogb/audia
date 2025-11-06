#!/bin/bash
# Deploy do backend (FastAPI + Celery + Redis) na VM2

set -e

echo "🚀 Deploying Backend to VM2..."

# Verificar variáveis
if [ -z "$OCI_VM2_HOST" ]; then
    echo "❌ OCI_VM2_HOST não definido"
    exit 1
fi

# Copiar arquivos para VM
echo "📦 Copiando arquivos..."
rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
    apps/backend/ ubuntu@$OCI_VM2_HOST:~/audia/backend/

rsync -avz deploy/docker-compose.yml ubuntu@$OCI_VM2_HOST:~/audia/
rsync -avz .env ubuntu@$OCI_VM2_HOST:~/audia/

# Executar deploy na VM
echo "🔧 Executando deploy na VM2..."
ssh ubuntu@$OCI_VM2_HOST << 'EOF'
    cd ~/audia

    # Instalar Docker se necessário
    if ! command -v docker &> /dev/null; then
        echo "Instalando Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
    fi

    # Instalar Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "Instalando Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi

    # Deploy
    echo "Iniciando containers..."
    docker-compose down
    docker-compose build
    docker-compose up -d

    echo "✅ Deploy concluído!"

    # Health check
    sleep 10
    curl -f http://localhost:8000/health || echo "⚠️  Health check falhou"
EOF

echo "✅ Deploy na VM2 concluído!"
