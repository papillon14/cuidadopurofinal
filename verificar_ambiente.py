# verificar_ambiente.py
# Confere se está tudo pronto para rodar o Cuidado Puro e diz o que falta.
# Uso (no terminal do VS Code, dentro da pasta cuidado_puro):
#     Linux:    python3 verificar_ambiente.py
#     Windows:  python verificar_ambiente.py

import importlib.util
import socket
import sqlite3
import sys
import urllib.request
from pathlib import Path

try:  # acentos certos no terminal do Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PASTA = Path(__file__).resolve().parent
WINDOWS = sys.platform.startswith("win")
PY = "python" if WINDOWS else "python3"
ATIVAR = r"venv\Scripts\activate" if WINDOWS else "source venv/bin/activate"
problemas = []


def ok(texto):
    print("  [OK]    " + texto)


def aviso(texto, dica):
    print("  [AVISO] " + texto)
    print("          -> " + dica)


def falta(texto, conserto):
    print("  [FALTA] " + texto)
    print("          -> " + conserto)
    problemas.append(texto)


print("\n=== 1. PYTHON ===")
v = sys.version_info
if v >= (3, 8):
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
else:
    falta(f"Python {v.major}.{v.minor} é antigo demais (precisa 3.8 ou mais)",
          "Peça ao técnico do laboratório para atualizar o Python 3.")

print("\n=== 2. AMBIENTE VIRTUAL (venv) ===")
dentro_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
if dentro_venv:
    ok("O venv está ATIVADO (aparece (venv) no começo da linha)")
elif (PASTA / "venv").is_dir():
    aviso("A pasta venv existe, mas NÃO está ativada",
          f"Rode: {ATIVAR}   (se estiver usando o PLANO B sem venv, pode ignorar)")
else:
    aviso("Sem venv (tudo bem se estiver usando o PLANO B)",
          f"Para criar: {PY} -m venv venv   e depois   {ATIVAR}")

print("\n=== 3. BIBLIOTECAS (requirements.txt) ===")
for nome in ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "qrcode"]:
    if importlib.util.find_spec(nome) is None:
        falta(f"{nome} não instalado",
              "Rode: pip install -r requirements.txt   (PLANO B: pip3 install --user -r requirements.txt)")
    else:
        try:
            from importlib.metadata import version
            ok(f"{nome} {version(nome)}")
        except Exception:
            ok(nome)

print("\n=== 4. ARQUIVOS DO PROJETO ===")
arquivos = ["requirements.txt", "main.py", "database.py", "models.py", "schemas.py", "seguranca.py",
            "monitor.py", "carregar_exemplos.py",
            "rotas/acesso.py", "rotas/pessoas.py", "rotas/conversas.py", "rotas/agenda.py",
            "rotas/saude.py", "rotas/mensalidades.py", "rotas/sac.py", "rotas/painel.py",
            "banco_sql/01_tabelas.sql", "banco_sql/02_inserts.sql", "banco_sql/03_consultas.sql",
            "site/index.html", "site/js/config.js", "site/js/app.js", "site/manifest.json",
            "site/service-worker.js"]
faltando = [a for a in arquivos if not (PASTA / a).is_file()]
if faltando:
    for a in faltando:
        falta(f"{a} não encontrado", "Abra no VS Code a pasta cuidado_puro INTEIRA (Arquivo > Abrir Pasta).")
else:
    ok(f"Os {len(arquivos)} arquivos principais estão no lugar")

print("\n=== 5. BANCO SQLite (cuidado_puro.db) ===")
banco = PASTA / "cuidado_puro.db"
if not banco.is_file():
    aviso("cuidado_puro.db ainda não existe (normal na primeira vez)",
          f"Rode: {PY} carregar_exemplos.py   (ou ligue a API, que cria o banco vazio só com o ADM)")
else:
    try:
        con = sqlite3.connect(banco)
        tabelas = {t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if len(tabelas) >= 26:
            n_cui = con.execute("SELECT COUNT(*) FROM cuidador").fetchone()[0]
            n_pac = con.execute("SELECT COUNT(*) FROM paciente").fetchone()[0]
            n_eq = con.execute("SELECT COUNT(*) FROM equipe_interna").fetchone()[0]
            ok(f"{len(tabelas)} tabelas. Cuidadores: {n_cui} · Pacientes: {n_pac} · Equipe: {n_eq}")
        else:
            falta(f"Só existem {len(tabelas)} tabelas (precisa 26)", f"Rode: {PY} carregar_exemplos.py")
        con.close()
    except Exception as erro:
        falta(f"Não consegui abrir o banco ({erro})", f"Desligue a API e rode: {PY} carregar_exemplos.py")

print("\n=== 6. API (porta 8000) ===")
s = socket.socket()
s.settimeout(1)
porta_ocupada = s.connect_ex(("127.0.0.1", 8000)) == 0
s.close()
if porta_ocupada:
    try:
        resposta = urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=3).read().decode()
        if "Cuidado Puro" in resposta:
            ok("A API está LIGADA. Site: http://127.0.0.1:8000   Swagger: http://127.0.0.1:8000/docs")
        else:
            falta("A porta 8000 está ocupada por OUTRO programa",
                  "Feche o outro terminal (Ctrl+C) e ligue de novo a API do Cuidado Puro.")
    except Exception:
        falta("A porta 8000 está ocupada mas não é o Cuidado Puro",
              "Feche o outro terminal com Ctrl+C (pode ser a API do Teste 1/2) e ligue esta.")
else:
    aviso("A API ainda não está ligada (normal antes do uvicorn)",
          "Para ligar: uvicorn main:app --reload   (PLANO B: " + PY + " -m uvicorn main:app --reload)")

print("\n" + "=" * 60)
if problemas:
    print(f"FALTAM {len(problemas)} COISA(S). Resolva de cima para baixo e rode este script de novo.")
else:
    print("TUDO PRONTO! Pode seguir para o teste.")
print("=" * 60 + "\n")
