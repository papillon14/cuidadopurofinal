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


def atualizar_banco_existente():
    """Atualiza um banco que JÁ EXISTE (ex.: o da nuvem) sem perder nenhum dado.

    Versão 3.1: a regra do horário mudou de "fim > início" para "fim <> início",
    para aceitar plantão que termina no dia seguinte. O SQLite não deixa alterar
    uma regra CHECK, então a tabela 'cuidado' é recriada com a regra nova e os
    dados são copiados (receita oficial do SQLite). Roda sozinho ao ligar a API
    e só faz alguma coisa uma vez."""
    import re
    import sqlite3
    if not ARQUIVO_BANCO.exists():
        return
    con = sqlite3.connect(ARQUIVO_BANCO, isolation_level=None, timeout=15)
    try:
        linha = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='cuidado'").fetchone()
        if not linha or "hora_fim > hora_inicio" not in linha[0]:
            return                                   # banco novo ou já atualizado
        indices = [r[0] for r in con.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='cuidado' AND sql IS NOT NULL")]
        sql_novo = linha[0].replace("hora_fim > hora_inicio", "hora_fim <> hora_inicio")
        sql_novo = re.sub(r'CREATE TABLE\s+"?cuidado"?', "CREATE TABLE cuidado_novo", sql_novo, count=1)
        con.execute("PRAGMA foreign_keys = OFF")
        con.execute("BEGIN")
        con.execute(sql_novo)
        con.execute("INSERT INTO cuidado_novo SELECT * FROM cuidado")
        con.execute("DROP TABLE cuidado")
        con.execute("ALTER TABLE cuidado_novo RENAME TO cuidado")
        for sql in indices:
            con.execute(sql)
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("chave estrangeira quebrada na atualização")
        con.execute("COMMIT")
        print("Banco atualizado: agendamentos agora aceitam terminar no dia seguinte.")
    except Exception:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.execute("PRAGMA foreign_keys = ON")
        con.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
