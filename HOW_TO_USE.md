# 🚀 Como Usar o Sistema de RPA Crawler

Este sistema coleta dados de dois sites diferentes usando web scraping com Selenium (Chromium) e filas RabbitMQ.

## 📋 Pré-requisitos

- **Docker** e **Docker Compose** (v2: `docker compose` ou v1: `docker-compose`)
- (Opcional) `make`, `curl`, `jq` para testes via terminal
- **Mac com Apple Silicon:** o `docker-compose.yml` já usa `platform: linux/arm64` para postgres, rabbitmq, api e worker


## 🎯 Início Rápido

### 1. Iniciar o Sistema

```bash
docker compose up --build -d
```

Ou com Make:

```bash
make build && make up
```

Isso iniciará:
- ✅ PostgreSQL em `localhost:5432`
- ✅ RabbitMQ em `localhost:5672` (UI: `localhost:15672`)
- ✅ API REST em `localhost:8000`
- ✅ 2 Workers processando jobs (Chromium headless via Selenium Manager)

### 2. Testar os Scrapers

#### Opção A: Script Interativo (🌟 Recomendado)

```bash
./test_crawlers.sh
```

Escolha:
1. Testar Hockey
2. Testar Oscar
3. Testar ambos
4. Listar jobs
5. Ver resultados

#### Opção B: Comandos Diretos

**Coletar dados de Hockey:**
```bash
curl -X POST http://localhost:8000/crawl/hockey | jq
```

**Coletar dados de Oscar:**
```bash
curl -X POST http://localhost:8000/crawl/oscar | jq
```

**Coletar AMBOS:**
```bash
curl -X POST http://localhost:8000/crawl/all | jq
```

#### Opção C: Interface Web (Swagger)

Abra: http://localhost:8000/docs

Clique em "Try it out" nos endpoints e execute!

### 3. Verificar Resultados

**Ver status de um job:**
```bash
curl http://localhost:8000/jobs/{job_id} | jq
```

**Ver resultados de um job:**
```bash
curl http://localhost:8000/jobs/{job_id}/results | jq
```

**Ver TODOS os dados de Hockey:**
```bash
curl http://localhost:8000/results/hockey?limit=10 | jq
```

**Ver TODOS os dados de Oscar:**
```bash
curl http://localhost:8000/results/oscar?limit=10 | jq
```

## 📊 Exemplo Completo

```bash
# 1. Iniciar coleta de Hockey
RESPONSE=$(curl -s -X POST http://localhost:8000/crawl/hockey)
echo $RESPONSE | jq

# 2. Extrair o job_id
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# 3. Aguardar alguns segundos para processar
sleep 10

# 4. Verificar status
curl -s http://localhost:8000/jobs/$JOB_ID | jq '.status'

# 5. Quando status for "completed", buscar resultados
curl -s http://localhost:8000/jobs/$JOB_ID/results | jq '.results[:3]'
```

## 🏒 Scraper de Hockey

**Site:** https://www.scrapethissite.com/pages/forms/

**O que coleta:**
- Nome dos times de hockey
- Estatísticas por ano (vitórias, derrotas, gols, etc.)
- Todas as páginas disponíveis

**Exemplo de resultado:**
```json
{
  "name": "Boston Bruins",
  "year": 1990,
  "wins": 44,
  "losses": 24,
  "losses_ot": 4,
  "wins_percentage": 0.646,
  "goals_for": 289,
  "goals_against": 232,
  "goal_difference": 57
}
```

## 🎬 Scraper de Oscar

**Site:** https://www.scrapethissite.com/pages/ajax-javascript/

**O que coleta:**
- Filmes indicados ao Oscar
- Número de indicações e prêmios
- Se ganhou melhor filme

**Exemplo de resultado:**
```json
{
  "title": "The Shape of Water",
  "year": 2017,
  "nominations": 13,
  "awards": 4,
  "best_picture": true
}
```

## 🔍 Monitoramento

### Ver Logs da API
```bash
docker compose logs -f api
```
Ou: `make logs-api`

### Ver Logs dos Workers
```bash
docker compose logs -f worker
```
Ou: `make logs-worker`

### RabbitMQ Management UI
Acesse: http://localhost:15672
- User: `guest`
- Pass: `guest`

Veja:
- Quantos jobs estão na fila
- Taxa de processamento
- Workers conectados

## ⚙️ Comandos Úteis

```bash
# Parar sistema
docker compose down

# Reconstruir imagens (após mudar Dockerfile ou requirements)
docker compose build

# Escalar workers (4 workers simultâneos)
docker compose up -d --scale worker=4

# Limpar tudo (incluindo volumes e dados)
docker compose down -v

# Ver status dos containers
docker compose ps
```

*(Substitua `docker compose` por `docker-compose` se usar Compose v1.)*

## 📱 Usando o Makefile

Se você tem `make` instalado:

```bash
make help          # Ver todos os comandos
make up            # Iniciar sistema
make test-menu     # Menu de testes
make logs          # Ver logs
make down          # Parar sistema
make clean         # Limpar tudo
```

## 🐛 Resolução de Problemas

### Job fica "pending" para sempre
**Causa:** Workers não estão rodando

**Solução:**
```bash
docker-compose ps worker
docker-compose logs worker
```

### Erro de conexão com banco
**Causa:** PostgreSQL ainda não iniciou completamente

**Solução:** Aguarde mais alguns segundos e tente novamente

### Scraper falha
**Causa:** Site pode estar fora do ar ou mudou estrutura

**Solução:**
```bash
curl http://localhost:8000/jobs/{job_id} | jq '.error_message'
```

### RabbitMQ não conecta
**Causa:** Serviço ainda não está pronto

**Solução:**
```bash
docker-compose logs rabbitmq
# Aguarde até ver "Server startup complete"
```

## 📚 Documentação Adicional

- [QUICKSTART.md](QUICKSTART.md) - Início super rápido
- [USAGE.md](USAGE.md) - Guia completo de uso
- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura do sistema
- [README.md](README.md) - Especificação original do projeto

## 🎯 Status dos Jobs

| Status | Significado |
|--------|-------------|
| `pending` | Job criado, na fila do RabbitMQ |
| `running` | Worker está processando |
| `completed` | Concluído com sucesso ✅ |
| `failed` | Erro no processamento ❌ |

## ✅ Checklist de Teste

- [ ] Sistema inicia sem erros
- [ ] API responde em http://localhost:8000
- [ ] RabbitMQ UI acessível em http://localhost:15672
- [ ] POST /crawl/hockey retorna job_id
- [ ] POST /crawl/oscar retorna job_id
- [ ] GET /jobs mostra os jobs criados
- [ ] Jobs mudam de "pending" → "running" → "completed"
- [ ] GET /jobs/{job_id}/results retorna dados coletados
- [ ] Workers aparecem nos logs processando jobs

## 💡 Dicas

1. **Use jq para JSON bonito:** `curl ... | jq`
2. **Script de teste é seu amigo:** `./test_crawlers.sh`
3. **Swagger é interativo:** http://localhost:8000/docs
4. **Monitore filas:** http://localhost:15672
5. **Logs são úteis:** `docker-compose logs -f`

---

**Pronto para começar?**

```bash
docker-compose up --build
./test_crawlers.sh
```

🎉 **Divirta-se coletando dados!**
