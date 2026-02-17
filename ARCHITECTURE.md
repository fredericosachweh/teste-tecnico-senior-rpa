# 🏗️ Arquitetura do Sistema

## Visão Geral

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  RabbitMQ   │────▶│   Workers   │
│    (API)    │     │   (Queue)   │     │  (Crawlers) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       │            ┌─────────────┐            │
       └───────────▶│  PostgreSQL │◀───────────┘
                    │    (Data)   │
                    └─────────────┘
```

## Componentes

### 1. FastAPI (API REST)
**Arquivo:** `app/main.py`

**Responsabilidades:**
- Receber requisições HTTP dos clientes
- Criar jobs no banco de dados
- Publicar mensagens na fila RabbitMQ
- Retornar status e resultados dos jobs

**Endpoints:**
- `POST /crawl/hockey` - Agenda coleta de Hockey
- `POST /crawl/oscar` - Agenda coleta de Oscar
- `POST /crawl/all` - Agenda ambas coletas
- `GET /jobs` - Lista todos os jobs
- `GET /jobs/{job_id}` - Status de um job específico
- `GET /jobs/{job_id}/results` - Resultados de um job
- `GET /results/hockey` - Todos os dados de Hockey
- `GET /results/oscar` - Todos os dados de Oscar

### 2. RabbitMQ (Fila de Mensagens)
**Arquivo:** `app/queue.py`

**Responsabilidades:**
- Gerenciar fila de jobs assíncronos
- Garantir entrega das mensagens
- Balancear carga entre workers
- Persistir mensagens (durable queue)

**Configuração:**
- Queue Name: `crawl_jobs`
- Durable: `True`
- QoS: `prefetch_count=1` (um job por worker)
- Socket timeout e `connection_attempts` para falha rápida se RabbitMQ estiver indisponível
- `publish_jobs()` para publicar vários jobs em uma única conexão (ex.: `/crawl/all`)

### 3. Workers (Processadores)
**Arquivo:** `app/worker.py`

**Responsabilidades:**
- Consumir mensagens da fila RabbitMQ
- Executar os scrapers (Hockey ou Oscar)
- Atualizar status dos jobs no banco
- Salvar resultados no banco de dados

**Fluxo:**
1. Recebe mensagem com `{job_id, job_type}`
2. Atualiza job para status `running`
3. Executa scraper apropriado
4. Salva resultados no banco
5. Atualiza job para `completed` ou `failed`
6. Faz ACK da mensagem

**Escalabilidade:**
- Configurado com 2 réplicas por padrão
- Pode ser escalado: `docker-compose up --scale worker=4`

### 4. PostgreSQL (Banco de Dados)
**Arquivos:** `app/database.py`, `app/models/*.py` (jobs, hockey_teams, films)

**Tabelas:**

#### `jobs`
```sql
- id (PK)
- job_id (UUID, unique)
- job_type (enum: hockey, oscar)
- status (enum: pending, running, completed, failed)
- created_at
- started_at
- completed_at
- error_message
- results_count
```

#### `hockey_team`
```sql
- id (PK)
- name (UNIQUE)
```

#### `hockey_team_historic`
```sql
- id (PK)
- team_id (FK → hockey_team.id)
- year
- wins, losses, losses_ot
- wins_percentage
- goals_for, goals_against
- goal_difference
- job_id (rastreabilidade)
```

#### `films`
```sql
- id (PK)
- title (UNIQUE)
```
(Oscar metadata fica em `oscar_winner_films`.)

#### `oscar_winner_films`
```sql
- id (PK)
- film_id (FK → films.id, ON DELETE CASCADE)
- year
- nominations
- awards
- best_picture (boolean)
- job_id (rastreabilidade)
```

### 5. Scrapers (Coletores)
**Arquivo:** `app/crawlers/crawler.py`

#### HockeyHistoricScraper
**Site:** https://www.scrapethissite.com/pages/forms/

**Estratégia:**
- HTML tradicional com paginação
- Selenium com Chrome headless
- Itera por todas as páginas (`?page_num=N`)
- Extrai dados de tabela HTML

**Dados coletados:**
- Nome do time
- Ano
- Estatísticas (vitórias, derrotas, gols, etc.)

#### OscarScraper
**Site:** https://www.scrapethissite.com/pages/ajax-javascript/

**Estratégia:**
- Dados via AJAX (requisições HTTP por ano)
- Selenium para obter lista de anos na página; `urllib` para chamadas à API AJAX por ano
- Cria/Reutiliza `Film` por título; grava `OscarWinnerFilm` com `film_id`

**Dados coletados:**
- Título do filme (tabela `films`, único por título)
- Ano, indicações, prêmios, melhor filme (tabela `oscar_winner_films`)

## Fluxo de Dados

### Fluxo de Criação de Job

```
1. Cliente faz POST /crawl/hockey
           ↓
2. API cria Job (status=pending) no PostgreSQL
           ↓
3. API publica mensagem {job_id, job_type} no RabbitMQ
           ↓
4. API retorna job_id para o cliente imediatamente
```

### Fluxo de Processamento

```
1. Worker consome mensagem da fila
           ↓
2. Worker atualiza Job (status=running) no PostgreSQL
           ↓
3. Worker executa scraper apropriado
           ↓
4. Scraper coleta dados do site
           ↓
5. Scraper salva dados no PostgreSQL com job_id
           ↓
6. Worker atualiza Job (status=completed, results_count)
           ↓
7. Worker faz ACK da mensagem no RabbitMQ
```

### Fluxo de Consulta

```
1. Cliente faz GET /jobs/{job_id}
           ↓
2. API consulta PostgreSQL
           ↓
3. API retorna status do job
```

```
1. Cliente faz GET /jobs/{job_id}/results
           ↓
2. API verifica se job está completed
           ↓
3. API consulta dados relacionados ao job_id
           ↓
4. API retorna resultados
```

## Padrões e Boas Práticas

### 1. Processamento Assíncrono
- Jobs são processados em background
- API responde imediatamente
- Cliente pode consultar status depois

### 2. Rastreabilidade
- Cada dado coletado tem `job_id`
- Possível saber qual job coletou cada dado
- Histórico completo de execuções

### 3. Tratamento de Erros
- Erros são capturados e salvos em `error_message`
- Jobs com erro ficam com status `failed`
- Mensagens com erro podem ser reprocessadas

### 4. Idempotência
- Declarações de queue são idempotentes
- Criação de tabelas é idempotente
- Workers podem ser reiniciados sem problemas

### 5. Escalabilidade Horizontal
- Workers podem ser escalados independentemente
- RabbitMQ distribui jobs entre workers
- Banco suporta conexões concorrentes

### 6. Containerização
- Cada componente em container separado
- Isolamento de dependências
- Fácil deploy e replicação

## Tecnologias

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| Runtime | Python | **3.12** |
| API | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ |
| Validação | Pydantic | 2.0+ |
| Banco | PostgreSQL | 16 |
| Fila | RabbitMQ | 3 |
| Scraping | Selenium | 4.24+ |
| Browser | Chrome | Stable |
| Container | Docker | Latest |
| Orquestração | Docker Compose | Latest |

## Scripts e ferramentas

| Script | Uso |
|--------|-----|
| `python -m app.init_db` | Garante que o banco existe e cria/atualiza tabelas |

## Desenvolvimento e qualidade

- **Testes:** `pytest` em `app/tests` e `app/crawlers` (modelos, API, crawlers).
- **Lint/format:** Ruff e Black (config em `pyproject.toml`).
- **Pre-commit:** `.pre-commit-config.yaml` — hooks para trailing whitespace, end-of-file, YAML/JSON, Black, Ruff e Pytest. Instalação: `pre-commit install`.

## Melhorias Futuras

1. **Cache:** Redis para cache de resultados
2. **Retry:** Política de retry para jobs falhados
3. **Dead Letter Queue:** Fila separada para erros
4. **Métricas:** Prometheus + Grafana
5. **Rate Limiting:** Limitar chamadas aos sites
6. **Webhook:** Notificar conclusão de jobs
7. **Agendamento:** Celery Beat para jobs periódicos
8. **API Keys:** Autenticação na API
