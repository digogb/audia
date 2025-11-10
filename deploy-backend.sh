#!/bin/bash
# Script de deploy do backend na VM OCI

set -e

BACKEND_IP="204.216.185.65"
BACKEND_USER="ubuntu"

echo "🚀 Deploy do Backend Audia"
echo "=========================="
echo "IP: $BACKEND_IP"
echo ""

# 1. Testar conexão SSH
echo "📡 Testando conexão SSH..."
if ! ssh -o ConnectTimeout=5 $BACKEND_USER@$BACKEND_IP "echo 'Conectado!'" 2>/dev/null; then
    echo "❌ Erro: Não foi possível conectar via SSH"
    echo "   Verifique:"
    echo "   - Security Lists no OCI (porta 22 aberta)"
    echo "   - Firewall interno da VM (iptables)"
    echo "   - Chave SSH (~/.ssh/id_rsa)"
    exit 1
fi

echo "✅ Conexão SSH OK"
echo ""

# 2. Atualizar sistema e instalar Docker
echo "📦 Instalando Docker na VM..."
ssh $BACKEND_USER@$BACKEND_IP << 'ENDSSH'
    set -e

    # Atualizar sistema
    sudo apt update
    sudo apt upgrade -y

    # Instalar dependências
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common ffmpeg

    # Adicionar repositório Docker
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Instalar Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Adicionar usuário ao grupo docker
    sudo usermod -aG docker $USER

    echo "✅ Docker instalado!"
ENDSSH

echo "✅ Docker instalado"
echo ""

# 3. Copiar credenciais OCI
echo "🔐 Copiando credenciais OCI..."
if [ -d ~/.oci ]; then
    scp -r ~/.oci $BACKEND_USER@$BACKEND_IP:~/
    ssh $BACKEND_USER@$BACKEND_IP "chmod 600 ~/.oci/oci_api_key.pem ~/.oci/config"
    echo "✅ Credenciais OCI copiadas"
else
    echo "⚠️  Diretório ~/.oci não encontrado localmente"
    echo "   Configure as credenciais OCI manualmente na VM"
fi
echo ""

# 4. Clonar repositório
echo "📥 Clonando repositório..."
ssh $BACKEND_USER@$BACKEND_IP << 'ENDSSH'
    set -e

    # Remover se já existe
    rm -rf audia

    # Clonar
    git clone https://github.com/digogb/audia.git
    cd audia

    echo "✅ Repositório clonado"
ENDSSH

echo "✅ Repositório clonado"
echo ""

# 5. Criar arquivo .env
echo "⚙️  Configurando .env..."
if [ -f .env ]; then
    scp .env $BACKEND_USER@$BACKEND_IP:~/audia/
    echo "✅ Arquivo .env copiado"
else
    echo "⚠️  Arquivo .env não encontrado localmente"
    echo "   Você precisará criar manualmente na VM"
fi
echo ""

# 6. Iniciar containers
echo "🐳 Iniciando containers Docker..."
ssh $BACKEND_USER@$BACKEND_IP << 'ENDSSH'
    set -e

    cd audia/deploy

    # Parar containers antigos se existirem
    docker compose down 2>/dev/null || true

    # Iniciar novos containers
    docker compose up -d --build

    # Aguardar containers iniciarem
    sleep 10

    # Verificar status
    docker compose ps

    echo "✅ Containers iniciados"
ENDSSH

echo "✅ Containers iniciados"
echo ""

# 7. Testar API
echo "🧪 Testando API..."
sleep 5
if curl -f http://$BACKEND_IP:8000/health 2>/dev/null; then
    echo "✅ API funcionando!"
else
    echo "⚠️  API não respondeu (pode levar alguns minutos para iniciar)"
fi
echo ""

echo "✅ Deploy do backend concluído!"
echo ""
echo "📝 Próximos passos:"
echo "   - Verifique logs: ssh $BACKEND_USER@$BACKEND_IP 'cd audia/deploy && docker compose logs -f'"
echo "   - Acesse API: http://$BACKEND_IP:8000/docs"
echo "   - Acesse Flower: http://$BACKEND_IP:5555 (se ativado)"
