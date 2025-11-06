# 🔧 Troubleshooting - Problema de Login

## 📋 Problema Relatado

O formulário de login dá refresh na página e limpa os dados quando clica em "Entrar".

## ✅ Correções Aplicadas

### 1. Proteção contra SSR (Server-Side Rendering)
- Adicionei verificações `typeof window !== 'undefined'` nos interceptores do axios
- Isso evita erros quando o código tenta acessar `localStorage` no servidor

### 2. Prevenção de Refresh
- Adicionado `e.stopPropagation()` no handler do formulário
- Adicionado delay de 500ms antes de redirecionar

### 3. Logs de Debug
- Adicionados console.logs em todas as etapas da autenticação
- Isso permite ver exatamente onde o processo está falhando

## 🧪 Como Testar Agora

### Passo 1: Recarregue o Frontend
```bash
# No terminal do frontend (Ctrl+C para parar, depois):
npm run dev
```

### Passo 2: Limpe o Cache do Navegador
1. Abra o DevTools (F12)
2. Clique com botão direito no botão de atualizar
3. Selecione "Limpar cache e recarregar" (ou use Ctrl+Shift+R)

### Passo 3: Teste o Login
1. Acesse: http://localhost:3000
2. Abra o Console (F12 → Console)
3. Preencha os dados:
   ```
   Email: teste@exemplo.com
   Senha: senha12345
   ```
4. Clique em "Entrar"

### Passo 4: Observe os Logs

Você deve ver no Console (e eles **não devem sumir**):

```
🔐 Iniciando autenticação... {isLogin: true, email: "teste@exemplo.com"}
🔑 Fazendo login...
📡 Chamando API de login... {email: "teste@exemplo.com"}
✅ Resposta da API: {access_token: "...", refresh_token: "..."}
💾 Salvando tokens no localStorage...
👤 Buscando dados do usuário...
✅ Dados do usuário: {id: 1, email: "teste@exemplo.com", ...}
✅ Login bem-sucedido! {id: 1, ...}
🚀 Redirecionando para dashboard...
```

## 🔍 Diagnósticos

### Se as mensagens aparecem e somem rapidamente:
**Problema**: A página está recarregando (F5)
**Causa**: Provavelmente erro de JavaScript não capturado
**Solução**:
1. Abra DevTools ANTES de clicar em "Entrar"
2. Na aba Console, clique em "Preserve log" ✅
3. Tente fazer login novamente
4. Me envie o erro vermelho que aparecer

### Se aparecer erro de CORS:
```
Access to XMLHttpRequest at 'http://localhost:8000/v1/auth/login'
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solução**: Backend precisa reiniciar
```bash
make stop
make dev
```

### Se aparecer erro de Network:
```
POST http://localhost:8000/v1/auth/login net::ERR_CONNECTION_REFUSED
```

**Solução**: Backend não está rodando
```bash
# Verificar se backend está up
curl http://localhost:8000/health

# Se não responder, reinicie
make dev
```

### Se aparecer erro 400 (Bad Request):
```
❌ Erro na autenticação: {detail: "Invalid credentials"}
```

**Causa**: Credenciais incorretas
**Solução**:
1. Se é login: Usuário não existe, tente criar conta primeiro
2. Se é registro: Email já existe, tente fazer login

### Se não aparecer nenhuma mensagem:
**Problema**: JavaScript não está executando
**Solução**:
1. Verifique se há erros de compilação no terminal do npm
2. Procure erros vermelhos no Console
3. Tente recompilar: Ctrl+C no npm e `npm run dev` novamente

## 🆘 Teste Alternativo

Se o frontend ainda não funcionar, teste direto com curl:

```bash
# Registrar usuário
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"novo@teste.com","username":"novo","password":"senha12345"}'

# Fazer login
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"novo@teste.com","password":"senha12345"}'
```

Se esses comandos funcionarem, o problema está **apenas no frontend**.

## 📱 Teste com HTML Simples

Criei um arquivo de teste. Abra no navegador:

```bash
xdg-open test-login.html
# ou
firefox test-login.html
```

Este arquivo testa a API diretamente sem Next.js.

## 🐛 Informações para Debug

Se ainda não funcionar, me envie:

1. **Screenshot do Console** (F12 → Console) após tentar fazer login
2. **Screenshot da aba Network** (F12 → Network) mostrando as requisições
3. **Logs do terminal** onde o npm está rodando
4. **Resultado de**: `curl http://localhost:8000/health`

## 📝 Mudanças nos Arquivos

Arquivos modificados para corrigir o problema:

1. `apps/frontend/app/login/page.tsx`
   - Adicionado `e.stopPropagation()`
   - Adicionado delay antes de redirecionar
   - Adicionados logs de debug

2. `apps/frontend/lib/auth.ts`
   - Adicionados logs de debug em login()

3. `apps/frontend/lib/api-client.ts`
   - Adicionado `typeof window !== 'undefined'` nos interceptores
   - Proteção contra SSR

## ✅ Próximos Passos

Após o login funcionar:

1. ✅ Teste criar uma nova conta
2. ✅ Teste fazer logout
3. ✅ Teste acessar o dashboard
4. ✅ Teste fazer upload (vai falhar sem credenciais OCI, mas deve mostrar a interface)

---

*Última atualização: 2025-11-01*
