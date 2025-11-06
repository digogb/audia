.PHONY: help setup dev test build deploy-vm1 deploy-vm2 logs clean

# Variáveis
DOCKER_COMPOSE = docker-compose -f deploy/docker-compose.yml
BACKEND_DIR = apps/backend
FRONTEND_DIR = apps/frontend

help: ## Mostra esta mensagem de ajuda
	@echo "Audia - Comandos disponíveis:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Instala todas as dependências
	@echo "Instalando dependências do backend..."
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	@echo "Instalando dependências do frontend..."
	cd $(FRONTEND_DIR) && npm install
	@echo "Copiando .env.example para .env"
	cp .env.example .env
	@echo "✅ Setup concluído! Edite o arquivo .env com suas credenciais."

dev: ## Inicia ambiente de desenvolvimento com Docker
	@echo "Iniciando stack de desenvolvimento..."
	$(DOCKER_COMPOSE) up --build

dev-detached: ## Inicia ambiente de desenvolvimento em background
	@echo "Iniciando stack em background..."
	$(DOCKER_COMPOSE) up -d --build

dev-frontend: ## Inicia apenas o frontend (desenvolvimento local)
	@echo "Iniciando frontend em modo dev..."
	cd $(FRONTEND_DIR) && npm run dev

dev-backend: ## Inicia apenas o backend (desenvolvimento local)
	@echo "Iniciando backend em modo dev..."
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload

stop: ## Para todos os containers
	@echo "Parando containers..."
	$(DOCKER_COMPOSE) down

restart: ## Reinicia todos os containers
	@echo "Reiniciando containers..."
	$(DOCKER_COMPOSE) restart

logs: ## Mostra logs de todos os containers
	$(DOCKER_COMPOSE) logs -f

logs-backend: ## Mostra logs do backend
	$(DOCKER_COMPOSE) logs -f backend

logs-worker: ## Mostra logs do worker
	$(DOCKER_COMPOSE) logs -f worker

test: ## Roda todos os testes
	@echo "Rodando testes do backend..."
	cd $(BACKEND_DIR) && pytest -v --cov=app --cov-report=term-missing
	@echo "Rodando testes do frontend..."
	cd $(FRONTEND_DIR) && npm test

test-backend: ## Roda apenas testes do backend
	cd $(BACKEND_DIR) && pytest -v --cov=app

test-frontend: ## Roda apenas testes do frontend
	cd $(FRONTEND_DIR) && npm test

lint: ## Roda linters em todo o código
	@echo "Linting backend..."
	cd $(BACKEND_DIR) && ruff check app/
	cd $(BACKEND_DIR) && mypy app/
	@echo "Linting frontend..."
	cd $(FRONTEND_DIR) && npm run lint

format: ## Formata código automaticamente
	@echo "Formatando backend..."
	cd $(BACKEND_DIR) && black app/
	cd $(BACKEND_DIR) && ruff check --fix app/
	@echo "Formatando frontend..."
	cd $(FRONTEND_DIR) && npm run format

build: ## Builda todas as imagens Docker
	@echo "Building Docker images..."
	$(DOCKER_COMPOSE) build

push: ## Faz push das imagens para registry (configure antes)
	@echo "Pushing images to registry..."
	# TODO: Configure seu registry Docker
	# docker push your-registry/audia-backend:latest
	# docker push your-registry/audia-frontend:latest

deploy-vm1: ## Deploy do frontend na VM1 (Oracle Cloud)
	@echo "Deploying to VM1 (Frontend)..."
	./deploy/scripts/deploy-vm1.sh

deploy-vm2: ## Deploy do backend na VM2 (Oracle Cloud)
	@echo "Deploying to VM2 (Backend)..."
	./deploy/scripts/deploy-vm2.sh

deploy-all: deploy-vm2 deploy-vm1 ## Deploy completo (VM1 + VM2)

shell-backend: ## Abre shell no container do backend
	$(DOCKER_COMPOSE) exec backend bash

shell-worker: ## Abre shell no container do worker
	$(DOCKER_COMPOSE) exec worker bash

db-migrate: ## Roda migrações do banco de dados
	$(DOCKER_COMPOSE) exec backend python -c "from app.core.database import init_db; init_db()"

db-reset: ## Reseta o banco de dados (CUIDADO!)
	@echo "⚠️  ATENÇÃO: Isso vai deletar todos os dados!"
	@read -p "Tem certeza? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) exec backend python -c "from app.core.database import drop_db, init_db; drop_db(); init_db()"; \
		echo "✅ Banco de dados resetado"; \
	fi

clean: ## Remove containers, volumes e imagens
	@echo "Limpando containers e volumes..."
	$(DOCKER_COMPOSE) down -v
	@echo "Removendo imagens..."
	docker rmi audia-backend audia-worker 2>/dev/null || true
	@echo "✅ Limpeza concluída"

clean-all: clean ## Limpeza completa (inclui cache)
	@echo "Removendo cache Python..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Removendo node_modules..."
	rm -rf $(FRONTEND_DIR)/node_modules
	@echo "Removendo .next..."
	rm -rf $(FRONTEND_DIR)/.next
	@echo "✅ Limpeza completa concluída"

health: ## Verifica saúde dos serviços
	@echo "Verificando saúde dos serviços..."
	@curl -f http://localhost:8000/health || echo "❌ Backend não está respondendo"
	@curl -f http://localhost:8000/ready || echo "❌ Backend não está pronto"
	@curl -f http://localhost:3000 || echo "❌ Frontend não está respondendo"

stats: ## Mostra estatísticas dos containers
	$(DOCKER_COMPOSE) stats

ps: ## Lista containers em execução
	$(DOCKER_COMPOSE) ps

init-oci: ## Inicializa recursos no Oracle Cloud
	@echo "Inicializando recursos OCI..."
	./deploy/scripts/setup-oci.sh

backup: ## Faz backup do banco de dados e índices FAISS
	@echo "Fazendo backup..."
	mkdir -p backups
	$(DOCKER_COMPOSE) exec backend tar czf - /app/data | cat > backups/backup-$$(date +%Y%m%d-%H%M%S).tar.gz
	@echo "✅ Backup salvo em backups/"

restore: ## Restaura backup mais recente
	@echo "Restaurando backup..."
	@LATEST=$$(ls -t backups/*.tar.gz | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "❌ Nenhum backup encontrado"; \
	else \
		cat $$LATEST | $(DOCKER_COMPOSE) exec -T backend tar xzf - -C /; \
		echo "✅ Backup restaurado: $$LATEST"; \
	fi

version: ## Mostra versão da aplicação
	@grep "APP_VERSION" .env.example | cut -d '=' -f2

.DEFAULT_GOAL := help
