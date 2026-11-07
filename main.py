# main.py -> o arquivo principal: liga tudo.
#   1. Cria as tabelas (se o banco ainda não existir)
#   2. Libera o CORS (o site do Go Live conversa com a API)
#   3. Junta as rotas (pasta rotas/) — todas começam com /api
#   4. Serve o próprio site: abra http://127.0.0.1:8000 e o site já aparece
#
# Rodar:  uvicorn main:app --reload
# Swagger: http://127.0.0.1:8000/docs
import time
import traceback
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

import models
import monitor
from database import Base, SessionLocal, engine
from seguranca import gerar_hash
from rotas import acesso, agenda, conversas, mensalidades, painel, pessoas, sac, saude

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Cuidado Puro — API",
    version="3.0",
    description="Plataforma de home care: paciente, cuidador, família e equipe interna. "
                "Para testar rotas com login: faça POST /api/login (ou /api/equipe/login), copie o "
                "token e clique no cadeado **Authorize**.",
)

# CORS: libera o navegador para o site conversar com a API pelo fetch
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def medir_e_registrar(request: Request, chamar_rota):
    """Mede o tempo de cada requisição (painel do Backend) e grava erros 500."""
    inicio = time.perf_counter()
    try:
        resposta = await chamar_rota(request)
    except Exception as erro:  # erro inesperado no código
        db = SessionLocal()
        try:
            db.add(models.LogErro(origem="api", mensagem=f"{type(erro).__name__}: {erro}"[:500],
                                  detalhe=traceback.format_exc()[-4000:], pagina=request.url.path,
                                  criado_em=datetime.now()))
            db.commit()
        finally:
            db.close()
        resposta = JSONResponse(status_code=500,
                                content={"detail": "Erro interno. A equipe de backend foi avisada."})
    if request.url.path.startswith("/api"):
        rota = request.scope.get("route")
        nome = f"{request.method} {getattr(rota, 'path', request.url.path)}"
        monitor.registrar(nome, (time.perf_counter() - inicio) * 1000, resposta.status_code)
    return resposta


@app.exception_handler(IntegrityError)
async def dado_repetido(request: Request, erro: IntegrityError):
    """Rede de segurança: se o banco recusar (UNIQUE/CHECK), responde 409 em vez de 500."""
    return JSONResponse(status_code=409, content={"detail": "O banco recusou: dado repetido ou inválido. "
                                                            f"({str(erro.orig)[:120]})"})


for modulo in (acesso, pessoas, conversas, agenda, saude, mensalidades, sac, painel):
    app.include_router(modulo.router)


@app.get("/api/status", tags=["0. Status"])
def status_api():
    return {"status": "online", "projeto": "Cuidado Puro", "versao": app.version,
            "mensagem": "API no ar! Abra /docs para o Swagger ou / para o site."}


@app.on_event("startup")
def garantir_primeiro_acesso():
    """Se o banco estiver vazio (sem rodar carregar_exemplos.py), cria o mínimo
    para o sistema funcionar: os planos, os catálogos e o primeiro ADM."""
    db = SessionLocal()
    try:
        if db.query(models.Plano).count() == 0:
            db.add_all([
                models.Plano(nome="Básico", publico="cuidador", valor=29.90, limite_conversas=3, ordem_busca=1,
                             descricao="Aparece na busca e recebe pedidos de conversa (até 3 conversas abertas)."),
                models.Plano(nome="Padrão", publico="cuidador", valor=59.90, pode_iniciar_conversa=1, ordem_busca=2,
                             descricao="Conversas ilimitadas, aparece acima do Básico e pode chamar pacientes."),
                models.Plano(nome="Premium", publico="cuidador", valor=99.90, pode_iniciar_conversa=1, destaque=1,
                             relatorio=1, ordem_busca=3,
                             descricao="Tudo do Padrão + topo da busca, selo Destaque e relatório de visitas."),
                models.Plano(nome="Paciente", publico="paciente", valor=29.90, pode_iniciar_conversa=1,
                             descricao="Acesso completo: busca de cuidadores, chat, agenda e Modo Pós-Alta."),
            ])
        if db.query(models.Necessidade).count() == 0:
            for nome, grau in [("Alzheimer / demência", "alto"), ("Monitoramento de sinais vitais", "leve"),
                               ("Sonda nasoenteral (SNE)", "alto"), ("Recuperação de cirurgia", "moderado"),
                               ("Acompanhamento pediátrico", "leve"),
                               ("Mobilidade reduzida / risco de queda", "moderado"),
                               ("Diabetes (controle de glicemia)", "moderado"),
                               ("Companhia e apoio nas atividades do dia", "leve")]:
                db.add(models.Necessidade(nome_necessidade=nome, grau_dependencia=grau))
        if db.query(models.Habilidade).count() == 0:
            for nome, restrita in [("Medicação injetável (IM / SC)", 1), ("Manejo e higiene de sonda", 1),
                                   ("Curativos", 1), ("Banho e higiene pessoal", 0),
                                   ("Alimentação e hidratação", 0), ("Aferição de pressão e glicemia", 0),
                                   ("Acompanhamento em consultas e passeios", 0),
                                   ("Cuidados com idosos com demência", 0)]:
                db.add(models.Habilidade(nome_habilidade=nome, restrita_tecnico=restrita))
        if db.query(models.EquipeInterna).count() == 0:
            db.add(models.EquipeInterna(nome="Administrador", cpf="000.000.000-00", telefone="(00) 00000-0000",
                                        cidade="Maringá", email="adm@cuidadopuro.com",
                                        senha_hash=gerar_hash("admin123"), papel="ADM"))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------
# O SITE: a pasta site/ é servida em http://127.0.0.1:8000/
# (fica por último, para não "engolir" as rotas /api e /docs)
# ---------------------------------------------------------------------
PASTA_SITE = Path(__file__).resolve().parent / "site"
if PASTA_SITE.exists():
    app.mount("/", StaticFiles(directory=PASTA_SITE, html=True), name="site")
else:
    @app.get("/", include_in_schema=False)
    def inicio():
        return RedirectResponse("/docs")
