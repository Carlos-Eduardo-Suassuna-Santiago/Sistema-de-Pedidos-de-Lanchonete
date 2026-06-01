from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

# Banco único, mas schemas separados por módulo (prefixo no nome da tabela)
# Use DATABASE_URL para permitir sobrescrever a conexão em containers
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lanchonete_modular.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
