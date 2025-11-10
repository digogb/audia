#!/bin/bash

echo "🧪 TESTANDO ACESSO EXTERNO À APLICAÇÃO AUDIA"
echo "=============================================="
echo ""

IP="164.152.240.91"
PASSOU=0
FALHOU=0

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "IP da Aplicação: $IP"
echo ""

# Teste 1: Backend Health
echo "Teste 1: Backend Health Check (porta 8000)"
echo -n "  Testando http://$IP:8000/health ... "

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$IP:8000/health 2>/dev/null)

if [ "$RESPONSE" == "200" ]; then
    echo -e "${GREEN}✅ PASSOU${NC} (HTTP $RESPONSE)"
    ((PASSOU++))
else
    echo -e "${RED}❌ FALHOU${NC} (HTTP $RESPONSE)"
    ((FALHOU++))
fi

# Teste 2: Backend Docs
echo "Teste 2: Documentação da API (porta 8000)"
echo -n "  Testando http://$IP:8000/docs ... "

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$IP:8000/docs 2>/dev/null)

if [ "$RESPONSE" == "200" ]; then
    echo -e "${GREEN}✅ PASSOU${NC} (HTTP $RESPONSE)"
    ((PASSOU++))
else
    echo -e "${RED}❌ FALHOU${NC} (HTTP $RESPONSE)"
    ((FALHOU++))
fi

# Teste 3: Frontend
echo "Teste 3: Frontend Next.js (porta 3000)"
echo -n "  Testando http://$IP:3000 ... "

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$IP:3000 2>/dev/null)

if [ "$RESPONSE" == "200" ]; then
    echo -e "${GREEN}✅ PASSOU${NC} (HTTP $RESPONSE)"
    ((PASSOU++))
else
    echo -e "${RED}❌ FALHOU${NC} (HTTP $RESPONSE)"
    ((FALHOU++))
fi

# Teste 4: Verificar conteúdo do frontend
echo "Teste 4: Verificar se o frontend retorna HTML"
echo -n "  Verificando conteúdo HTML ... "

CONTENT=$(curl -s --connect-timeout 5 http://$IP:3000 2>/dev/null | grep -c "Audia" 2>/dev/null || echo "0")

if [ "$CONTENT" -gt "0" ]; then
    echo -e "${GREEN}✅ PASSOU${NC} (Encontrou 'Audia' no HTML)"
    ((PASSOU++))
else
    echo -e "${RED}❌ FALHOU${NC} (Não encontrou 'Audia' no HTML)"
    ((FALHOU++))
fi

echo ""
echo "=============================================="
echo "RESULTADO DOS TESTES"
echo "=============================================="
echo -e "✅ Passaram: ${GREEN}$PASSOU${NC}"
echo -e "❌ Falharam: ${RED}$FALHOU${NC}"
echo ""

if [ $FALHOU -eq 0 ]; then
    echo -e "${GREEN}🎉 SUCESSO! Todos os testes passaram!${NC}"
    echo ""
    echo "Você pode acessar a aplicação em:"
    echo "  • Frontend: http://$IP:3000"
    echo "  • Backend API: http://$IP:8000/docs"
    echo ""
    echo "Próximos passos:"
    echo "  1. Abra http://$IP:3000 no navegador"
    echo "  2. Faça cadastro de um usuário"
    echo "  3. Faça login"
    echo "  4. Teste o upload e transcrição de áudio"
else
    echo -e "${YELLOW}⚠️  Alguns testes falharam.${NC}"
    echo ""
    echo "Possíveis causas:"
    if [ $FALHOU -eq 4 ]; then
        echo -e "${RED}  ❌ Security List da OCI ainda não foi configurado${NC}"
        echo "     Siga as instruções em: CONFIGURAR_SECURITY_LIST_OCI.md"
    elif [ $FALHOU -eq 1 ] || [ $FALHOU -eq 2 ]; then
        echo -e "${YELLOW}  ⚠️  Security List parcialmente configurado${NC}"
        echo "     Verifique se adicionou as regras para AMBAS as portas: 3000 e 8000"
    fi
    echo ""
    echo "Após configurar, execute este script novamente:"
    echo "  bash testar-acesso-externo.sh"
fi

echo ""
