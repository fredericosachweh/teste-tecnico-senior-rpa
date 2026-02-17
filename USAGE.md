# Guia de Uso - Sistema de RPA Crawler

Para desenvolvimento local e testes, recomenda-se **qualquer versão do Python 3.12** (menor que 3.13, por causa do Pydantic). Ver [README.md](README.md#python).

## 🚀 Início Rápido

### 1. Iniciar o sistema completo

```bash
docker-compose up --build
```

Isso iniciará:
- PostgreSQL (porta 5432)
- RabbitMQ (porta 5672 + Management UI em http://localhost:15672)
- API REST (porta 8000)
- 2 Workers para processar os crawlers

### 2. Acessar a documentação da API

Abra no navegador: http://localhost:8000/docs

Você verá a interface Swagger com todos os endpoints disponíveis.

---

## 📡 Endpoints Disponíveis

### Iniciar Coletas (Assíncronas)

#### 1. Coletar dados do Hockey

```bash
curl -X POST http://localhost:8000/crawl/hockey
```

**Resposta:**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_type": "hockey",
  "status": "pending",
  "created_at": "2026-02-14T10:00:00",
  "results_count": 0
}
```

#### 2. Coletar dados do Oscar

```bash
curl -X POST http://localhost:8000/crawl/oscar
```

**Resposta:**
```json
{
  "job_id": "234e5678-e89b-12d3-a456-426614174001",
  "job_type": "oscar",
  "status": "pending",
  "created_at": "2026-02-14T10:01:00",
  "results_count": 0
}
```

#### 3. Coletar AMBOS de uma vez

```bash
curl -X POST http://localhost:8000/crawl/all
```

**Resposta:**
```json
{
  "jobs": [
    {
      "job_id": "345e6789-e89b-12d3-a456-426614174002",
      "job_type": "hockey",
      "status": "pending"
    },
    {
      "job_id": "456e7890-e89b-12d3-a456-426614174003",
      "job_type": "oscar",
      "status": "pending"
    }
  ]
}
```

---

### Acompanhar Jobs

#### 1. Listar todos os jobs

```bash
curl http://localhost:8000/jobs
```

**Resposta:**
```json
[
  {
    "job_id": "123e4567-e89b-12d3-a456-426614174000",
    "job_type": "hockey",
    "status": "completed",
    "created_at": "2026-02-14T10:00:00",
    "started_at": "2026-02-14T10:00:05",
    "completed_at": "2026-02-14T10:02:30",
    "results_count": 2400
  }
]
```

#### 2. Verificar status de um job específico

```bash
curl http://localhost:8000/jobs/{job_id}
```

**Status possíveis:**
- `pending` - Job na fila, aguardando processamento
- `running` - Job sendo processado pelo worker
- `completed` - Job concluído com sucesso
- `failed` - Job falhou (ver `error_message`)

#### 3. Obter resultados de um job

```bash
curl http://localhost:8000/jobs/{job_id}/results
```

**Resposta (Hockey):**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "job_type": "hockey",
  "results_count": 2400,
  "results": [
    {
      "id": 1,
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
  ]
}
```

**Resposta (Oscar):**
```json
{
  "job_id": "234e5678-e89b-12d3-a456-426614174001",
  "status": "completed",
  "job_type": "oscar",
  "results_count": 500,
  "results": [
    {
      "id": 1,
      "title": "The Shape of Water",
      "year": 2017,
      "nominations": 13,
      "awards": 4,
      "best_picture": true
    }
  ]
}
```

---

### Consultar Todos os Resultados

#### 1. Todos os dados de Hockey

```bash
curl http://localhost:8000/results/hockey?limit=100
```

#### 2. Todos os dados de Oscar

```bash
curl http://localhost:8000/results/oscar?limit=100
```

---

## 🔍 Monitoramento

### RabbitMQ Management UI

Acesse: http://localhost:15672

**Credenciais:**
- Username: `guest`
- Password: `guest`

Aqui você pode:
- Ver quantos jobs estão na fila
- Monitorar taxa de processamento
- Ver mensagens em tempo real

### Logs dos Workers

```bash
# Ver logs da API
docker-compose logs -f api

# Ver logs dos workers
docker-compose logs -f worker
```

---

## 🧪 Exemplos de Uso Completo

### Exemplo 1: Coletar Hockey e acompanhar

```bash
# 1. Iniciar coleta
RESPONSE=$(curl -s -X POST http://localhost:8000/crawl/hockey)
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')

echo "Job criado: $JOB_ID"

# 2. Aguardar alguns segundos
sleep 5

# 3. Verificar status
curl http://localhost:8000/jobs/$JOB_ID | jq

# 4. Se completado, buscar resultados
curl http://localhost:8000/jobs/$JOB_ID/results | jq '.results[:5]'
```

### Exemplo 2: Coletar tudo e comparar

```bash
# 1. Iniciar ambos
curl -X POST http://localhost:8000/crawl/all | jq

# 2. Listar jobs
curl http://localhost:8000/jobs | jq

# 3. Ver todos os resultados de Hockey
curl 'http://localhost:8000/results/hockey?limit=10' | jq

# 4. Ver todos os resultados de Oscar
curl 'http://localhost:8000/results/oscar?limit=10' | jq
```

---

## 🛠️ Desenvolvimento Local

### Sem Docker

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Iniciar PostgreSQL e RabbitMQ
docker-compose up postgres rabbitmq

# 3. Copiar variáveis de ambiente
cp .env.example .env

# 4. Em um terminal: iniciar API
uvicorn app.main:app --reload

# 5. Em outro terminal: iniciar worker
python -m app.worker
```

---

## 📊 Estrutura de Dados

### Hockey Team Historic
- `name` - Nome do time
- `year` - Ano
- `wins` - Vitórias
- `losses` - Derrotas
- `losses_ot` - Derrotas na prorrogação
- `wins_percentage` - Percentual de vitórias
- `goals_for` - Gols a favor
- `goals_against` - Gols contra
- `goal_difference` - Diferença de gols

### Oscar Films
- `title` - Título do filme
- `year` - Ano
- `nominations` - Número de indicações
- `awards` - Número de prêmios
- `best_picture` - Ganhou melhor filme (boolean)

---

## ⚙️ Configuração

Variáveis de ambiente (arquivo `.env`):

```bash
# Banco de dados
DATABASE_URL=postgresql://app:app@localhost:5432/app

# Fila de mensagens
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Selenium (headless mode)
HEADLESS=true
```

---

## 🐛 Troubleshooting

### Job fica "pending" para sempre
- Verifique se os workers estão rodando: `docker-compose ps`
- Verifique os logs: `docker-compose logs worker`

### Erro de conexão com banco
- Aguarde o PostgreSQL iniciar completamente
- Verifique: `docker-compose logs postgres`

### Scraper não funciona
- Certifique-se que `HEADLESS=true` está configurado
- Chrome precisa estar instalado no container (já está no Dockerfile)

---

## 🎯 Dicas

1. **Use jq** para formatar JSON: `curl ... | jq`
2. **Monitore workers** em tempo real: `docker-compose logs -f worker`
3. **Escale workers** se necessário: `docker-compose up --scale worker=4`
4. **RabbitMQ UI** é útil para debug de filas

---

## 📝 Notas

- Os scrapers usam Selenium com Chrome headless
- Jobs são processados de forma assíncrona via RabbitMQ
- Dados são persistidos no PostgreSQL com relação ao job_id
- Cada job tem rastreabilidade completa (pending → running → completed/failed)
