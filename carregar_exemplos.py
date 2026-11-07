# carregar_exemplos.py -> (re)cria o banco cuidado_puro.db com os dados de exemplo.
#
# Roda os MESMOS arquivos que você testa no SQL Fiddle:
#     banco_sql/01_tabelas.sql  e  banco_sql/02_inserts.sql
#
# Também serve para ZERAR o banco (ex.: toda manhã nos dias da feira):
# apaga tudo o que foi cadastrado e volta só com os exemplos.
#
# Uso:  1) desligue a API (Ctrl+C no terminal do uvicorn)
#       2) python3 carregar_exemplos.py
#       3) ligue a API de novo: uvicorn main:app --reload
import socket
import sqlite3
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
BANCO = PASTA / "cuidado_puro.db"


def api_ligada() -> bool:
    s = socket.socket()
    s.settimeout(0.5)
    ligada = s.connect_ex(("127.0.0.1", 8000)) == 0
    s.close()
    return ligada


if api_ligada() and "--forcar" not in sys.argv:
    print("ATENÇÃO: a API parece estar ligada (porta 8000).")
    print("Desligue o uvicorn com Ctrl+C e rode este comando de novo.")
    print("(Se tiver certeza de que não é a API do Cuidado Puro, use: python3 carregar_exemplos.py --forcar)")
    sys.exit(1)

# Apaga o banco antigo e os arquivos do modo WAL
for arquivo in (BANCO, Path(str(BANCO) + "-wal"), Path(str(BANCO) + "-shm")):
    if arquivo.exists():
        arquivo.unlink()

con = sqlite3.connect(BANCO)
for nome in ("01_tabelas.sql", "02_inserts.sql"):
    con.executescript((PASTA / "banco_sql" / nome).read_text(encoding="utf-8"))
    print(f"OK: {nome}")
con.execute("PRAGMA journal_mode = WAL")
con.commit()

contar = lambda tabela: con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
print(f"\nPronto! cuidado_puro.db criado com:")
print(f"  {contar('equipe_interna')} usuários da equipe, {contar('cuidador')} cuidadores, "
      f"{contar('paciente')} pacientes, {contar('familiar')} familiares")
print(f"  {contar('conversa')} conversas, {contar('cuidado')} agendamentos, "
      f"{contar('registro_diario')} registros de saúde")
con.close()
print("\nLogins de teste (senha):")
print("  ADM ........ adm@cuidadopuro.com (admin123)")
print("  equipe ..... suporte@ / sac@ / financeiro@ / marketing@ / comercial@ /")
print("               frontend@ / backend@ / banco@cuidadopuro.com (equipe123)")
print("  paciente ... tereza@email.com (cuidado123)")
print("  cuidador ... carlos.souza@email.com [Premium] / marcos.oliveira@email.com [Padrão] /")
print("               ana.silva@email.com [Básico] (cuidado123)")
print("  família .... mariana.lawson@email.com (cuidado123)")
