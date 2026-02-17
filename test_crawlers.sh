#!/bin/bash
# Script para testar os crawlers localmente

set -e

echo "🔍 Sistema de RPA Crawler - Script de Teste"
echo "==========================================="
echo ""

# Verificar se a API está rodando
echo "📡 Verificando API..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ API não está rodando em http://localhost:8000"
    echo "   Execute: docker-compose up"
    exit 1
fi
echo "✅ API está online"
echo ""

# Função para aguardar job completar
wait_for_job() {
    local job_id=$1
    local job_type=$2
    local max_wait=300  # 5 minutos
    local elapsed=0

    echo "⏳ Aguardando job $job_type completar..."

    while [ $elapsed -lt $max_wait ]; do
        status=$(curl -s "http://localhost:8000/jobs/$job_id" | jq -r '.status')

        if [ "$status" = "completed" ]; then
            echo "✅ Job $job_type completado!"
            return 0
        elif [ "$status" = "failed" ]; then
            echo "❌ Job $job_type falhou!"
            curl -s "http://localhost:8000/jobs/$job_id" | jq '.error_message'
            return 1
        fi

        echo "   Status: $status (${elapsed}s)"
        sleep 5
        elapsed=$((elapsed + 5))
    done

    echo "⏱️ Timeout aguardando job completar"
    return 1
}

# Menu
echo "Escolha uma opção:"
echo "1) Testar scraper de Hockey"
echo "2) Testar scraper de Oscar"
echo "3) Testar ambos"
echo "4) Listar todos os jobs"
echo "5) Ver resultados de Hockey"
echo "6) Ver resultados de Oscar"
echo ""
read -p "Opção [1-6]: " option

case $option in
    1)
        echo ""
        echo "🏒 Iniciando coleta de Hockey..."
        response=$(curl -s -X POST http://localhost:8000/crawl/hockey)
        job_id=$(echo $response | jq -r '.job_id')
        echo "Job ID: $job_id"
        echo ""

        if wait_for_job "$job_id" "hockey"; then
            echo ""
            echo "📊 Primeiros 5 resultados:"
            curl -s "http://localhost:8000/jobs/$job_id/results" | jq '.results[:5]'
        fi
        ;;

    2)
        echo ""
        echo "🎬 Iniciando coleta de Oscar..."
        response=$(curl -s -X POST http://localhost:8000/crawl/oscar)
        job_id=$(echo $response | jq -r '.job_id')
        echo "Job ID: $job_id"
        echo ""

        if wait_for_job "$job_id" "oscar"; then
            echo ""
            echo "📊 Primeiros 5 resultados:"
            curl -s "http://localhost:8000/jobs/$job_id/results" | jq '.results[:5]'
        fi
        ;;

    3)
        echo ""
        echo "🏒🎬 Iniciando coleta de AMBOS..."
        response=$(curl -s -X POST http://localhost:8000/crawl/all)
        echo $response | jq

        hockey_job_id=$(echo $response | jq -r '.jobs[0].job_id')
        oscar_job_id=$(echo $response | jq -r '.jobs[1].job_id')

        echo ""

        if wait_for_job "$hockey_job_id" "hockey"; then
            echo "📊 Resultados de Hockey:"
            curl -s "http://localhost:8000/jobs/$hockey_job_id/results" | jq '.results_count'
        fi

        echo ""

        if wait_for_job "$oscar_job_id" "oscar"; then
            echo "📊 Resultados de Oscar:"
            curl -s "http://localhost:8000/jobs/$oscar_job_id/results" | jq '.results_count'
        fi
        ;;

    4)
        echo ""
        echo "📋 Listando todos os jobs..."
        curl -s http://localhost:8000/jobs | jq
        ;;

    5)
        echo ""
        echo "🏒 Resultados de Hockey (últimos 10)..."
        curl -s "http://localhost:8000/results/hockey?limit=10" | jq
        ;;

    6)
        echo ""
        echo "🎬 Resultados de Oscar (últimos 10)..."
        curl -s "http://localhost:8000/results/oscar?limit=10" | jq
        ;;

    *)
        echo "Opção inválida"
        exit 1
        ;;
esac

echo ""
echo "✅ Teste concluído!"
