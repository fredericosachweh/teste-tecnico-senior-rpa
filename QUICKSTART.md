# 🚀 Início Rápido

## Opção 1: Usando Make (Recomendado)

```bash
# Ver todos os comandos disponíveis
make help

# Iniciar o sistema completo
make up

# Testar scrapers (menu interativo)
make test-menu
```

## Opção 2: Usando Docker Compose

```bash
# Iniciar tudo
docker-compose up --build

# Em outro terminal, testar:
./test_crawlers.sh
```

## Opção 3: Comandos manuais

```bash
# 1. Iniciar sistema
docker-compose up -d

# 2. Testar Hockey
curl -X POST http://localhost:8000/crawl/hockey

# 3. Testar Oscar
curl -X POST http://localhost:8000/crawl/oscar

# 4. Ver jobs
curl http://localhost:8000/jobs

# 5. Ver resultados de um job (use o job_id retornado)
curl http://localhost:8000/jobs/{job_id}/results
```

## 🌐 URLs Importantes

- **API Docs**: http://localhost:8000/docs
- **RabbitMQ UI**: http://localhost:15672 (guest/guest)
- **API Health**: http://localhost:8000/health

## 📚 Documentação Completa

Para mais detalhes, veja [USAGE.md](USAGE.md)
