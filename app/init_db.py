#!/usr/bin/env python
"""
Script para inicializar o banco de dados
Cria as tabelas necessárias
"""

from app.database import Base, engine, ensure_database_exists


def init_db():
    """Initialize database tables"""
    print("🗄️  Inicializando banco de dados...")

    # Ensure database exists
    try:
        ensure_database_exists()
        print("✅ Banco de dados verificado/criado")
    except Exception as e:
        print(f"⚠️  Não foi possível criar o banco: {e}")
        print("   (Ignorando se o banco já existe)")

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas/verificadas")
    print("✅ Banco de dados pronto!")


if __name__ == "__main__":
    init_db()
