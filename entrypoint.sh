#!/bin/bash
set -e

echo "🔄 Aguardando serviços..."

# Wait for PostgreSQL
echo "⏳ Aguardando PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  sleep 1
done
echo "✅ PostgreSQL pronto!"

# Wait for RabbitMQ
echo "⏳ Aguardando RabbitMQ..."
until nc -z ${RABBITMQ_HOST:-rabbitmq} ${RABBITMQ_PORT:-5672}; do
  sleep 1
done
echo "✅ RabbitMQ pronto!"

# Initialize database
echo "🗄️  Inicializando banco de dados..."
python -m app.init_db

echo "✅ Sistema pronto!"
echo ""

# Execute the main command
exec "$@"
