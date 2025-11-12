#!/bin/bash
# Script de deploy para produção
# Servidor: 164.152.240.91

set -e

PROD_IP="164.152.240.91"
PROD_USER="ubuntu"

echo "🚀 Deploy do Audia para Produção"
echo "=================================="
echo "Servidor: $PROD_IP"
echo ""

# Teste de conexão SSH
echo "📡 Testando conexão SSH..."
if ! ssh -o ConnectTimeout=10 $PROD_USER@$PROD_IP "echo 'Conectado!'" 2>/dev/null; then
    echo "❌ Erro: Não foi possível conectar via SSH"
    echo ""
    echo "Execute os seguintes comandos MANUALMENTE no servidor:"
    echo ""
    echo "  ssh $PROD_USER@$PROD_IP"
    echo "  cd /home/ubuntu/audia"
    echo "  git pull origin main"
    echo "  docker-compose -f deploy/docker-compose.yml up -d --build backend worker"
    echo "  docker ps"
    echo ""
    exit 1
fi

echo "✅ Conexão SSH OK"
echo ""

# Fazer deploy
echo "📥 Atualizando código..."
ssh $PROD_USER@$PROD_IP << 'ENDSSH'
    set -e

    cd /home/ubuntu/audia

    echo "🔄 Fazendo git pull..."
    git pull origin main

    echo "🐳 Rebuilding containers..."
    docker-compose -f deploy/docker-compose.yml up -d --build backend worker

    echo "⏳ Aguardando containers iniciarem..."
    sleep 15

    echo "📊 Status dos containers:"
    docker ps

    echo ""
    echo "✅ Deploy concluído!"
ENDSSH

echo ""
echo "✅ Deploy em produção concluído!"
echo ""
echo "📝 Verificações:"
echo "   - API: https://audia-api.digomattos.dev/health"
echo "   - Logs: ssh $PROD_USER@$PROD_IP 'docker logs audia-backend --tail 50'"
echo ""
