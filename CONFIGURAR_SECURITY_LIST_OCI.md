# Como Configurar Security List na OCI - Passo a Passo

## Situação Atual

✅ **Aplicação deployada com sucesso**
- Backend rodando na porta 8000
- Frontend rodando na porta 3000
- Firewall do SO (iptables) configurado

❌ **Problema**: Security List da OCI bloqueando acesso externo

## Informações da Sua Instância

- **IP Público**: 164.152.240.91
- **Região**: sa-vinhedo-1 (São Paulo - Vinhedo)
- **VNIC ID**: ocid1.vnic.oc1.sa-vinhedo-1.ab3ggljrc6xbthcjqzrghlx3wroedq5oazgi4md2go5ec52gm3uvczdf5usa
- **Tenancy OCID**: ocid1.tenancy.oc1..aaaaaaaa365nxvdyvmw3qe26miqonio2vety4hsol33a6b25v6kthabejy5q

---

## PASSO A PASSO COMPLETO

### 1. Acessar Console OCI
Abra o navegador e acesse: https://cloud.oracle.com

### 2. Fazer Login
- Selecione a região: **Brazil East (Vinhedo)**
- Faça login com suas credenciais

### 3. Navegar até a Instância
1. Clique no **menu hamburguer** (☰) no canto superior esquerdo
2. Vá em: **Compute** → **Instances**
3. Procure pela instância com IP **164.152.240.91**
4. Clique no **nome da instância**

### 4. Acessar a Virtual Cloud Network (VCN)
Na página de detalhes da instância:
1. Role até a seção **"Primary VNIC"** ou **"Instance Information"**
2. Você verá um link azul com o nome da **Subnet** (algo como "subnet-...")
3. Clique nesse link da subnet

### 5. Acessar Security Lists
Na página da Subnet:
1. No menu lateral esquerdo, procure por **"Security Lists"**
2. Você verá uma lista de Security Lists associadas à subnet
3. Clique na Security List chamada **"Default Security List for vcn-..."**

### 6. Ver Regras Atuais (Ingress Rules)
1. Você verá abas no topo: **Ingress Rules** e **Egress Rules**
2. Certifique-se de estar na aba **"Ingress Rules"**
3. Veja quais portas já estão liberadas (provavelmente só SSH na porta 22)

### 7. Adicionar Nova Regra - FRONTEND (Porta 3000)
1. Clique no botão **"Add Ingress Rules"**
2. Preencha o formulário:
   - **Stateless**: deixe desmarcado
   - **Source Type**: CIDR
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: TCP
   - **Source Port Range**: deixe em branco (ou "All")
   - **Destination Port Range**: `3000`
   - **Description**: `Audia Frontend - Next.js`
3. Clique em **"Add Ingress Rules"** (botão azul no final)

### 8. Adicionar Nova Regra - BACKEND (Porta 8000)
Repita o processo:
1. Clique novamente em **"Add Ingress Rules"**
2. Preencha:
   - **Stateless**: deixe desmarcado
   - **Source Type**: CIDR
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: TCP
   - **Source Port Range**: deixe em branco
   - **Destination Port Range**: `8000`
   - **Description**: `Audia Backend - FastAPI`
3. Clique em **"Add Ingress Rules"**

---

## VERIFICAÇÃO

Após adicionar as regras, aguarde **30-60 segundos** e teste:

### Teste 1: Backend Health Check
Abra no navegador:
```
http://164.152.240.91:8000/health
```
Deve retornar:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "app": "Audia"
}
```

### Teste 2: Documentação da API
```
http://164.152.240.91:8000/docs
```
Deve abrir a interface Swagger da API.

### Teste 3: Frontend
```
http://164.152.240.91:3000
```
Deve abrir a aplicação Audia com a tela de login.

---

## TROUBLESHOOTING

### Se ainda não funcionar após adicionar as regras:

1. **Aguarde 1-2 minutos** - as regras podem demorar para propagar
2. **Limpe o cache do navegador** - Ctrl+Shift+R (ou Cmd+Shift+R no Mac)
3. **Tente em modo anônimo/privado** do navegador
4. **Verifique se adicionou na Security List correta** - a subnet deve ser a mesma da instância

### Como verificar se é problema de firewall OCI vs outro problema:

Via SSH na máquina local, execute:
```bash
# Teste de conexão da sua máquina local
curl -I http://164.152.240.91:3000
curl -I http://164.152.240.91:8000/health
```

Se esses comandos funcionarem da sua máquina mas não do navegador, pode ser:
- Cache do navegador
- Firewall local/corporativo
- Proxy

---

## EXEMPLO VISUAL DO FORMULÁRIO

Quando clicar em "Add Ingress Rules", você verá um formulário assim:

```
┌─────────────────────────────────────────────┐
│ Add Ingress Rules                           │
├─────────────────────────────────────────────┤
│                                             │
│ ☐ Stateless                                │
│                                             │
│ Source Type: ▼ CIDR                        │
│                                             │
│ Source CIDR: [0.0.0.0/0          ]         │
│                                             │
│ IP Protocol: ▼ TCP                         │
│                                             │
│ Source Port Range: [            ]          │
│                                             │
│ Destination Port Range: [3000    ]         │
│                                             │
│ Description: [Audia Frontend - Next.js]    │
│                                             │
│              [Add Ingress Rules]           │
└─────────────────────────────────────────────┘
```

---

## RESUMO DAS REGRAS A ADICIONAR

| Campo | Regra 1 (Frontend) | Regra 2 (Backend) |
|-------|-------------------|-------------------|
| Source CIDR | 0.0.0.0/0 | 0.0.0.0/0 |
| IP Protocol | TCP | TCP |
| Destination Port | 3000 | 8000 |
| Description | Audia Frontend | Audia Backend |

---

## APÓS CONFIGURAR

Quando tudo estiver funcionando, você terá:

- ✅ Frontend acessível em http://164.152.240.91:3000
- ✅ Backend acessível em http://164.152.240.91:8000
- ✅ Pode fazer login, upload de áudio e testar transcrições
- ✅ Aplicação pronta para uso!

---

## PRÓXIMOS PASSOS OPCIONAIS

Depois de verificar que está tudo funcionando:

1. **Configurar domínio personalizado** (ex: audia.seudominio.com.br)
2. **Adicionar HTTPS** com Let's Encrypt/Certbot
3. **Configurar backup automático** do banco SQLite
4. **Remover as VMs antigas x86** para economizar recursos
