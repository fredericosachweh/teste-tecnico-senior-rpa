.PHONY: help up down build logs test-hockey test-oscar test-all clean

# No Mac (arm64/aarch64) usa overlay com platform: linux/arm64. No Linux não define platform.
UNAME_M := $(shell uname -m)
export COMPOSE_FILE := docker-compose.yml$(if $(filter arm64 aarch64,$(UNAME_M)),:docker-compose.arm64.yml,)

help:
	@echo "🤖 Sistema de RPA Crawler"
	@echo ""
	@echo "Comandos disponíveis:"
	@echo "  make up          - Inicia todos os serviços (PostgreSQL, RabbitMQ, API, Workers)"
	@echo "  make down        - Para todos os serviços"
	@echo "  make build       - Rebuilda as imagens Docker"
	@echo "  make logs        - Mostra logs de todos os serviços"
	@echo "  make logs-api    - Mostra logs apenas da API"
	@echo "  make logs-worker - Mostra logs apenas dos Workers"
	@echo "  make test-hockey - Testa o scraper de Hockey"
	@echo "  make test-oscar  - Testa o scraper de Oscar"
	@echo "  make test-all    - Testa ambos os scrapers"
	@echo "  make test-menu   - Menu interativo de testes"
	@echo "  make clean       - Remove containers, volumes e imagens"
	@echo ""

up:
	@echo "🚀 Iniciando sistema..."
	docker-compose up -d
	@echo ""
	@echo "✅ Sistema iniciado!"
	@echo "📡 API: http://localhost:8000/docs"
	@echo "🐰 RabbitMQ UI: http://localhost:15672 (guest/guest)"
	@echo ""

down:
	@echo "🛑 Parando sistema..."
	docker-compose down
	@echo "✅ Sistema parado!"

build:
	@echo "🔨 Rebuilding images..."
	docker-compose build
	@echo "✅ Build completo!"

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-worker:
	docker-compose logs -f worker

test-hockey:
	@echo "🏒 Testando scraper de Hockey..."
	@curl -X POST http://localhost:8000/crawl/hockey | jq

test-oscar:
	@echo "🎬 Testando scraper de Oscar..."
	@curl -X POST http://localhost:8000/crawl/oscar | jq

test-all:
	@echo "🏒🎬 Testando ambos os scrapers..."
	@curl -X POST http://localhost:8000/crawl/all | jq

test-menu:
	@./test_crawlers.sh

clean:
	@echo "🧹 Limpando tudo..."
	docker-compose down -v --rmi local
	@echo "✅ Limpeza completa!"
