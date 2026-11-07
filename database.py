# database.py -> a "linha telefônica" até o banco SQLite
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

PASTA = Path(__file__).resolve().parent
ARQUIVO_BANCO = PASTA / "cuidado_puro.db"

# O banco é um ARQUIVO dentro da pasta do projeto. Sem servidor, sem senha.
URL_BANCO = f"sqlite:///{ARQUIVO_BANCO}"

engine = create_engine(URL_BANCO, connect_args={"check_same_thread": False, "timeout": 15})


@event.listens_for(engine, "connect")
def configurar_sqlite(conexao, _registro):
    cursor = conexao.cursor()
    # Liga a conferência das chaves estrangeiras (no SQLite vem DESLIGADA)
    cursor.execute("PRAGMA foreign_keys = ON")
    # WAL: várias pessoas lendo e gravando ao mesmo tempo sem travar.
    # Cria os arquivos cuidado_puro.db-wal e cuidado_puro.db-shm (é normal).
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
