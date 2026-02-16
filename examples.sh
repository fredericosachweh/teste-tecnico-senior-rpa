#!/bin/bash
# Exemplos práticos de uso da API via curl

BASE_URL="http://localhost:8000"

echo "🚀 Exemplos de Uso - RPA Crawler API"
echo "===================================="
echo ""

echo "📍 Base URL: $BASE_URL"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  CRIAR JOBS (Iniciar Coletas)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🏒 Coletar dados de Hockey:"
echo "curl -X POST $BASE_URL/crawl/hockey"
echo ""

echo "🎬 Coletar dados de Oscar:"
echo "curl -X POST $BASE_URL/crawl/oscar"
echo ""

echo "🏒🎬 Coletar AMBOS:"
echo "curl -X POST $BASE_URL/crawl/all"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  CONSULTAR JOBS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Listar todos os jobs:"
echo "curl $BASE_URL/jobs | jq"
echo ""

echo "🔍 Ver status de um job específico:"
echo "curl $BASE_URL/jobs/{job_id} | jq"
echo "# Exemplo: curl $BASE_URL/jobs/123e4567-e89b-12d3-a456-426614174000 | jq"
echo ""

echo "📊 Ver resultados de um job:"
echo "curl $BASE_URL/jobs/{job_id}/results | jq"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  CONSULTAR TODOS OS RESULTADOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🏒 Todos os dados de Hockey (10 primeiros):"
echo "curl '$BASE_URL/results/hockey?limit=10' | jq"
echo ""

echo "🎬 Todos os dados de Oscar (10 primeiros):"
echo "curl '$BASE_URL/results/oscar?limit=10' | jq"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  HEALTH CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "❤️  Verificar saúde da API:"
echo "curl $BASE_URL/health"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  EXEMPLO COMPLETO (com jq)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat << 'EOF'
# Criar job e salvar job_id
JOB_ID=$(curl -s -X POST http://localhost:8000/crawl/hockey | jq -r '.job_id')
echo "Job criado: $JOB_ID"

# Aguardar processamento
sleep 10

# Verificar status
STATUS=$(curl -s http://localhost:8000/jobs/$JOB_ID | jq -r '.status')
echo "Status: $STATUS"

# Se completo, buscar resultados
if [ "$STATUS" = "completed" ]; then
    curl -s http://localhost:8000/jobs/$JOB_ID/results | jq '.results[:5]'
fi
EOF
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  FILTROS E PAGINAÇÃO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📄 Limitar resultados (padrão 100):"
echo "curl '$BASE_URL/results/hockey?limit=20' | jq"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  MONITORAMENTO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Contar jobs por status:"
cat << 'EOF'
curl -s http://localhost:8000/jobs | jq '[.[] | .status] | group_by(.) | map({status: .[0], count: length})'
EOF
echo ""

echo "⏱️  Ver tempo de processamento do último job:"
cat << 'EOF'
curl -s http://localhost:8000/jobs | jq '.[0] | {
    job_id,
    status,
    created: .created_at,
    started: .started_at,
    completed: .completed_at,
    results_count
}'
EOF
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  FORMATAÇÃO DE RESULTADOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🎨 Apenas os títulos dos filmes:"
echo "curl -s '$BASE_URL/results/oscar?limit=10' | jq '.results[].title'"
echo ""

echo "🏆 Apenas filmes que ganharam Best Picture:"
cat << 'EOF'
curl -s 'http://localhost:8000/results/oscar?limit=100' | jq '.results[] | select(.best_picture == true) | {title, year, awards}'
EOF
echo ""

echo "🏒 Top 5 times por vitórias:"
cat << 'EOF'
curl -s 'http://localhost:8000/results/hockey?limit=100' | jq '.results | sort_by(-.wins) | .[:5] | .[] | {name, year, wins}'
EOF
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 DICAS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "• Use | jq para JSON formatado"
echo "• Use | jq -r para valores raw (sem aspas)"
echo "• Use jq para filtrar e transformar dados"
echo "• Salve job_id em variável para consultas posteriores"
echo "• Aguarde alguns segundos após criar job antes de consultar resultados"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 URLS ÚTEIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Swagger UI:    $BASE_URL/docs"
echo "📖 ReDoc:         $BASE_URL/redoc"
echo "❤️  Health:        $BASE_URL/health"
echo "🐰 RabbitMQ UI:   http://localhost:15672"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 COMEÇAR AGORA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Teste rápido:"
echo "curl -X POST $BASE_URL/crawl/hockey | jq"
echo ""
echo "# Ou use o script interativo:"
echo "./test_crawlers.sh"
echo ""
