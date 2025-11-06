#!/bin/bash
# Script para configurar recursos iniciais no Oracle Cloud Infrastructure

set -e

echo "🚀 Audia - Setup Oracle Cloud Infrastructure"
echo "=========================================="

# Verificar se OCI CLI está instalado
if ! command -v oci &> /dev/null; then
    echo "❌ OCI CLI não encontrado. Instale: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm"
    exit 1
fi

# Carregar variáveis de ambiente
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo ""
echo "📦 1. Criando Object Storage Bucket..."
oci os bucket create \
    --name "${OCI_BUCKET}" \
    --compartment-id "${OCI_COMPARTMENT_OCID}" \
    --namespace "${OCI_NAMESPACE}" \
    --public-access-type NoPublicAccess \
    2>/dev/null && echo "✅ Bucket criado" || echo "⚠️  Bucket já existe"

echo ""
echo "♻️  2. Configurando Lifecycle Policy (deletar após 90 dias)..."
cat > /tmp/lifecycle-policy.json <<EOF
{
  "items": [
    {
      "name": "delete-old-uploads",
      "action": "DELETE",
      "isEnabled": true,
      "objectNameFilter": {
        "inclusionPrefixes": ["uploads/"]
      },
      "timeAmount": 90,
      "timeUnit": "DAYS"
    }
  ]
}
EOF

oci os object-lifecycle-policy put \
    --bucket-name "${OCI_BUCKET}" \
    --namespace "${OCI_NAMESPACE}" \
    --from-json file:///tmp/lifecycle-policy.json \
    && echo "✅ Lifecycle policy configurada"

rm /tmp/lifecycle-policy.json

echo ""
echo "🖥️  3. Criando VMs Free Tier..."
echo "⚠️  ATENÇÃO: Criação de VMs deve ser feita via Console OCI ou manualmente"
echo "   - VM1 (Frontend): AMD E2.1.Micro, Ubuntu 22.04"
echo "   - VM2 (Backend): AMD E2.1.Micro, Ubuntu 22.04"
echo ""
echo "   Após criar as VMs, configure:"
echo "   - Security Lists: permitir portas 80, 443 (VM1) e 8000 (VM2)"
echo "   - SSH keys configuradas"
echo "   - IPs públicos anotados"

echo ""
echo "✅ Setup OCI concluído!"
echo ""
echo "📝 Próximos passos:"
echo "   1. Criar VMs via Console OCI"
echo "   2. Configurar Security Lists"
echo "   3. Anotar IPs públicos das VMs"
echo "   4. Adicionar IPs como secrets no GitHub"
echo "   5. Executar: make deploy-vm1 && make deploy-vm2"
