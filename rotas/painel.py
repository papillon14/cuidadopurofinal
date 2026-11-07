# rotas/painel.py -> PAINEL INTERNO. Um painel só; cada papel vê a sua parte.
#   ADM ......... tudo + cadastro da equipe
#   suporte ..... aprova/recusa cadastros, lista usuários
#   SAC ......... avaliações ruins e chamados
#   financeiro .. mensalidades, quem pagou, quem deve
#   marketing ... visitas, origem dos cadastros, parcerias, campanhas, cupons
#   comercial ... preço e regras dos planos, assinantes por plano
#   frontend .... páginas mais acessadas e erros do site
#   backend ..... API no ar, requisições, erros da API
#   banco ....... tamanho das tabelas, integridade e backup
import secrets
import sqlite3
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

import models
import monitor
import schemas
from database import ARQUIVO_BANCO, engine, get_db
from seguranca import Usuario, exige_papel, gerar_hash
from rotas.comum import (atualizar_atrasadas, criar_mensalidade, dados_cuidador, dados_paciente,
                         email_em_uso, iniciais, pegar, referencia)

router = APIRouter(prefix="/api/painel", tags=["8. Painel interno (equipe)"])

SECOES = {
    "ADM": ["geral", "equipe", "cadastros", "usuarios", "sac", "financeiro", "marketing",
            "comercial", "frontend", "backend", "banco"],
    "suporte": ["cadastros", "usuarios"],
    "SAC": ["sac"],
    "financeiro": ["financeiro"],
    "marketing": ["marketing"],
    "comercial": ["comercial"],
    "frontend": ["frontend"],
    "backend": ["backend"],
    "banco": ["banco"],
}


@router.get("/menu")
def menu(usuario: Usuario = Depends(exige_papel(*SECOES))):
    return {"nome": usuario.nome, "papel": usuario.papel, "iniciais": iniciais(usuario.nome),
            "secoes": SECOES[usuario.papel] + ["conta"]}


def _visitas_por_dia(db: Session, dias: int = 14):
    inicio = date.today() - timedelta(days=dias - 1)
    contagem = dict(db.query(func.date(models.Visita.criado_em), func.count())
                    .filter(models.Visita.criado_em >= datetime.combine(inicio, datetime.min.time()))
                    .group_by(func.date(models.Visita.criado_em)).all())
    return [{"data": (inicio + timedelta(days=i)).strftime("%d/%m"),
             "visitas": contagem.get(str(inicio + timedelta(days=i)), 0)} for i in range(dias)]


# =====================================================================
# ADM: visão geral e equipe
# =====================================================================
@router.get("/geral")
def visao_geral(usuario: Usuario = Depends(exige_papel()), db: Session = Depends(get_db)):
    atualizar_atrasadas(db)
    ref = referencia()
    mes = db.query(models.Assinatura).filter_by(referencia=ref).all()
    trinta = datetime.now() - timedelta(days=30)
    return {
        "usuarios": {
            "pacientes": db.query(models.Paciente).count(),
            "cuidadores": db.query(models.Cuidador).count(),
            "familiares": db.query(models.Familiar).count(),
            "equipe": db.query(models.EquipeInterna).filter_by(status="ativo").count(),
        },
        "pendentes": db.query(models.Paciente).filter_by(status_cadastro="pendente").count()
                     + db.query(models.Cuidador).filter_by(status_cadastro="pendente").count(),
        "visitas_30_dias": db.query(models.Visita).filter(models.Visita.criado_em >= trinta).count(),
        "visitas_por_dia": _visitas_por_dia(db),
        "receita_mes": round(sum(a.valor for a in mes if a.status_pagamento == "pago"), 2),
        "a_receber_mes": round(sum(a.valor for a in mes if a.status_pagamento != "pago"), 2),
        "atrasadas": db.query(models.Assinatura).filter_by(status_pagamento="atrasado").count(),
        "conversas_ativas": db.query(models.Conversa).filter_by(status="aceita").count(),
        "atendimentos_futuros": db.query(models.Cuidado).filter(
            models.Cuidado.data >= date.today(), models.Cuidado.status == "agendado").count(),
        "atendimentos_concluidos": db.query(models.Cuidado).filter_by(status="concluído").count(),
        "avaliacoes_sac": db.query(models.Avaliacao).filter_by(status_sac="nova").count(),
        "chamados_abertos": db.query(models.ChamadoSac).filter(models.ChamadoSac.status != "resolvido").count(),
        "nota_media_plataforma": round(db.query(func.avg(models.Avaliacao.nota)).scalar() or 0, 1),
    }


def _membro(m: models.EquipeInterna) -> dict:
    return {"id_equipe": m.id_equipe, "nome": m.nome, "email": m.email, "papel": m.papel, "cpf": m.cpf,
            "telefone": m.telefone, "cidade": m.cidade, "status": m.status, "data_criacao": m.data_criacao}


@router.get("/equipe")
def listar_equipe(usuario: Usuario = Depends(exige_papel()), db: Session = Depends(get_db)):
    return [_membro(m) for m in db.query(models.EquipeInterna).order_by(models.EquipeInterna.id_equipe)]


@router.post("/equipe", status_code=status.HTTP_201_CREATED)
def cadastrar_membro(dados: schemas.EquipeCreate, usuario: Usuario = Depends(exige_papel()),
                     db: Session = Depends(get_db)):
    """Só o ADM. Se não mandar senha, o sistema gera uma (o ADM passa para a pessoa)."""
    if email_em_uso(db, dados.email):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    if db.query(models.EquipeInterna).filter_by(cpf=dados.cpf).first():
        raise HTTPException(status_code=409, detail="Este CPF já está cadastrado.")
    senha = dados.senha or secrets.token_urlsafe(6)
    m = models.EquipeInterna(nome=dados.nome, cpf=dados.cpf, telefone=dados.telefone, cidade=dados.cidade,
                             email=dados.email, papel=dados.papel, senha_hash=gerar_hash(senha))
    db.add(m)
    db.commit()
    return {**_membro(m), "senha_inicial": senha}


@router.patch("/equipe/{id_equipe}")
def alterar_membro(id_equipe: int, dados: schemas.EquipeUpdate, usuario: Usuario = Depends(exige_papel()),
                   db: Session = Depends(get_db)):
    m = pegar(db, models.EquipeInterna, id_equipe, "Membro da equipe")
    if m.id_equipe == usuario.id and (dados.status == "inativo" or (dados.papel and dados.papel != "ADM")):
        raise HTTPException(status_code=409, detail="Você não pode tirar o seu próprio acesso de ADM.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(m, campo, valor)
    if m.status == "inativo":
        db.query(models.Sessao).filter_by(tipo_usuario="equipe", id_usuario=m.id_equipe).delete()
    db.commit()
    return _membro(m)


@router.post("/equipe/{id_equipe}/nova-senha")
def resetar_senha(id_equipe: int, usuario: Usuario = Depends(exige_papel()), db: Session = Depends(get_db)):
    m = pegar(db, models.EquipeInterna, id_equipe, "Membro da equipe")
    senha = secrets.token_urlsafe(6)
    m.senha_hash = gerar_hash(senha)
    db.commit()
    return {"mensagem": f"Nova senha de {m.nome} gerada.", "senha_inicial": senha}


# =====================================================================
# SUPORTE: cadastros e usuários
# =====================================================================
@router.get("/cadastros")
def cadastros(status_cadastro: str = "pendente", usuario: Usuario = Depends(exige_papel("suporte")),
              db: Session = Depends(get_db)):
    itens = []
    for p in db.query(models.Paciente).filter_by(status_cadastro=status_cadastro):
        itens.append({"tipo": "paciente", "id": p.id_paciente, "nome": p.nome, "email": p.email, "cpf": p.cpf,
                      "telefone": p.telefone, "cidade": p.cidade, "data_criacao": p.data_criacao,
                      "detalhes": {"Endereço": p.endereco, "Nascimento": p.data_nascimento.strftime("%d/%m/%Y"),
                                   "Responsável": p.nome_responsavel or "—",
                                   "Necessidades": ", ".join(n.nome_necessidade for n in p.necessidades) or "—",
                                   "Observações": p.observacoes or "—"}})
    for c in db.query(models.Cuidador).filter_by(status_cadastro=status_cadastro):
        itens.append({"tipo": "cuidador", "id": c.id_cuidador, "nome": c.nome, "email": c.email, "cpf": c.cpf,
                      "telefone": c.telefone, "cidade": c.cidade, "data_criacao": c.data_criacao,
                      "detalhes": {"Categoria": c.categoria_profissional, "COREN": c.numero_registro_coren or "—",
                                   "Idade": c.idade, "Plano": c.plano.nome,
                                   "Habilidades": ", ".join(h.nome_habilidade for h in c.habilidades) or "—",
                                   "Descrição": c.descricao or "—"}})
    return sorted(itens, key=lambda x: x["data_criacao"], reverse=True)


@router.post("/cadastros/{tipo}/{id_usuario}")
def decidir_cadastro(tipo: str, id_usuario: int, dados: schemas.StatusCadastro,
                     usuario: Usuario = Depends(exige_papel("suporte")), db: Session = Depends(get_db)):
    modelo = {"paciente": models.Paciente, "cuidador": models.Cuidador}.get(tipo)
    if modelo is None:
        raise HTTPException(status_code=422, detail="Tipo deve ser 'paciente' ou 'cuidador'.")
    registro = pegar(db, modelo, id_usuario, tipo.capitalize())
    registro.status_cadastro = dados.status
    db.commit()
    return {"mensagem": f"{registro.nome}: cadastro {dados.status}.", "status_cadastro": dados.status}


@router.get("/usuarios")
def usuarios(usuario: Usuario = Depends(exige_papel("suporte")), db: Session = Depends(get_db)):
    lista = []
    for p in db.query(models.Paciente):
        lista.append({"tipo": "paciente", "id": p.id_paciente, "nome": p.nome, "email": p.email,
                      "cidade": p.cidade, "status": p.status_cadastro, "plano": "Paciente",
                      "data_criacao": p.data_criacao})
    for c in db.query(models.Cuidador):
        lista.append({"tipo": "cuidador", "id": c.id_cuidador, "nome": c.nome, "email": c.email,
                      "cidade": c.cidade, "status": c.status_cadastro, "plano": c.plano.nome,
                      "data_criacao": c.data_criacao})
    for f in db.query(models.Familiar):
        lista.append({"tipo": "familiar", "id": f.id_familiar, "nome": f.nome, "email": f.email,
                      "cidade": "—", "status": "ativo", "plano": "—", "data_criacao": f.data_criacao})
    return sorted(lista, key=lambda x: x["data_criacao"], reverse=True)


# =====================================================================
# SAC: avaliações ruins e chamados
# =====================================================================
@router.get("/sac/avaliacoes")
def avaliacoes(somente_ruins: bool = True, usuario: Usuario = Depends(exige_papel("SAC")),
               db: Session = Depends(get_db)):
    q = db.query(models.Avaliacao)
    if somente_ruins:
        q = q.filter(models.Avaliacao.nota <= 2)
    return [{"id_avaliacao": a.id_avaliacao, "nota": a.nota, "comentario": a.comentario,
             "status_sac": a.status_sac, "criado_em": a.criado_em,
             "paciente": {"nome": a.paciente.nome, "telefone": a.paciente.telefone, "email": a.paciente.email},
             "cuidador": {"nome": a.cuidador.nome, "telefone": a.cuidador.telefone}}
            for a in q.order_by(models.Avaliacao.criado_em.desc())]


@router.patch("/sac/avaliacoes/{id_avaliacao}")
def tratar_avaliacao(id_avaliacao: int, dados: schemas.AvaliacaoSacUpdate,
                     usuario: Usuario = Depends(exige_papel("SAC")), db: Session = Depends(get_db)):
    a = pegar(db, models.Avaliacao, id_avaliacao, "Avaliação")
    a.status_sac = dados.status_sac
    db.commit()
    return {"id_avaliacao": a.id_avaliacao, "status_sac": a.status_sac}


@router.get("/sac/chamados")
def chamados(usuario: Usuario = Depends(exige_papel("SAC")), db: Session = Depends(get_db)):
    ordem = {"aberto": 0, "em andamento": 1, "resolvido": 2}
    lista = [{"id_chamado": c.id_chamado, "autor_tipo": c.autor_tipo, "nome": c.nome, "email": c.email,
              "assunto": c.assunto, "mensagem": c.mensagem, "status": c.status, "resposta": c.resposta,
              "criado_em": c.criado_em} for c in db.query(models.ChamadoSac)]
    return sorted(lista, key=lambda c: (ordem[c["status"]], -c["criado_em"].timestamp()))


@router.patch("/sac/chamados/{id_chamado}")
def responder_chamado(id_chamado: int, dados: schemas.ChamadoUpdate,
                      usuario: Usuario = Depends(exige_papel("SAC")), db: Session = Depends(get_db)):
    c = pegar(db, models.ChamadoSac, id_chamado, "Chamado")
    c.status = dados.status
    if dados.resposta is not None:
        c.resposta = dados.resposta
    db.commit()
    return {"id_chamado": c.id_chamado, "status": c.status, "resposta": c.resposta}


# =====================================================================
# FINANCEIRO
# =====================================================================
def _nome_usuario(db, a: models.Assinatura) -> str:
    modelo = models.Cuidador if a.tipo_usuario == "cuidador" else models.Paciente
    u = db.get(modelo, a.id_usuario)
    return u.nome if u else "(removido)"


@router.get("/financeiro")
def financeiro(referencia_mes: Optional[str] = None, status_pagamento: Optional[str] = None,
               usuario: Usuario = Depends(exige_papel("financeiro")), db: Session = Depends(get_db)):
    atualizar_atrasadas(db)
    ref = referencia_mes or referencia()
    q = db.query(models.Assinatura).filter_by(referencia=ref)
    todas = q.all()
    if status_pagamento:
        q = q.filter_by(status_pagamento=status_pagamento)
    meses = [r[0] for r in db.query(models.Assinatura.referencia).distinct()
             .order_by(models.Assinatura.referencia.desc())]
    historico = []
    for m in sorted(meses)[-6:]:
        linhas = db.query(models.Assinatura).filter_by(referencia=m).all()
        historico.append({"referencia": m,
                          "recebido": round(sum(a.valor for a in linhas if a.status_pagamento == "pago"), 2),
                          "a_receber": round(sum(a.valor for a in linhas if a.status_pagamento != "pago"), 2)})
    return {
        "referencia": ref, "meses": meses, "historico": historico,
        "resumo": {s: {"quantidade": sum(1 for a in todas if a.status_pagamento == s),
                       "valor": round(sum(a.valor for a in todas if a.status_pagamento == s), 2)}
                   for s in ("pago", "pendente", "atrasado")},
        "mensalidades": [{"id_assinatura": a.id_assinatura, "tipo_usuario": a.tipo_usuario,
                          "usuario": _nome_usuario(db, a), "plano": a.plano.nome, "valor": a.valor,
                          "codigo_cupom": a.codigo_cupom, "status_pagamento": a.status_pagamento,
                          "data_vencimento": a.data_vencimento, "data_pagamento": a.data_pagamento}
                         for a in q.order_by(models.Assinatura.status_pagamento.desc())],
    }


@router.post("/financeiro/{id_assinatura}/marcar-pago")
def marcar_pago(id_assinatura: int, usuario: Usuario = Depends(exige_papel("financeiro")),
                db: Session = Depends(get_db)):
    """Baixa manual (ex.: pagou por fora / comprovante enviado)."""
    a = pegar(db, models.Assinatura, id_assinatura, "Mensalidade")
    a.status_pagamento, a.data_pagamento = "pago", datetime.now()
    db.commit()
    return {"id_assinatura": a.id_assinatura, "status_pagamento": "pago"}


@router.post("/financeiro/gerar-proximo-mes")
def gerar_proximo_mes(usuario: Usuario = Depends(exige_papel("financeiro")), db: Session = Depends(get_db)):
    """Cria a mensalidade do próximo mês para todos os aprovados."""
    hoje = date.today()
    proximo = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1)
    ref = referencia(proximo)
    criadas = 0
    plano_paciente = db.query(models.Plano).filter_by(publico="paciente").first()
    for p in db.query(models.Paciente).filter_by(status_cadastro="aprovado"):
        if not db.query(models.Assinatura).filter_by(tipo_usuario="paciente", id_usuario=p.id_paciente,
                                                     referencia=ref).first():
            criar_mensalidade(db, "paciente", p.id_paciente, plano_paciente, ref)
            criadas += 1
    for c in db.query(models.Cuidador).filter_by(status_cadastro="aprovado"):
        if not db.query(models.Assinatura).filter_by(tipo_usuario="cuidador", id_usuario=c.id_cuidador,
                                                     referencia=ref).first():
            criar_mensalidade(db, "cuidador", c.id_cuidador, c.plano, ref)
            criadas += 1
    db.commit()
    return {"referencia": ref, "criadas": criadas}


# =====================================================================
# MARKETING
# =====================================================================
@router.get("/marketing")
def marketing(usuario: Usuario = Depends(exige_papel("marketing")), db: Session = Depends(get_db)):
    origens = {}
    for (origem,) in db.query(models.Paciente.origem).all() + db.query(models.Cuidador.origem).all():
        chave = origem or "Não informado"
        origens[chave] = origens.get(chave, 0) + 1
    trinta = datetime.now() - timedelta(days=30)
    visitas_30 = db.query(models.Visita).filter(models.Visita.criado_em >= trinta).count()
    cadastros_30 = db.query(models.Paciente).filter(models.Paciente.data_criacao >= trinta).count() \
        + db.query(models.Cuidador).filter(models.Cuidador.data_criacao >= trinta).count()
    referencias = dict(db.query(models.Visita.origem, func.count()).filter(models.Visita.origem.isnot(None))
                       .group_by(models.Visita.origem).order_by(func.count().desc()).limit(8).all())
    return {
        "visitas_por_dia": _visitas_por_dia(db),
        "visitas_30_dias": visitas_30,
        "cadastros_30_dias": cadastros_30,
        "conversao": round(100 * cadastros_30 / visitas_30, 1) if visitas_30 else None,
        "origem_cadastros": dict(sorted(origens.items(), key=lambda x: -x[1])),
        "sites_de_origem": referencias,
        "parcerias": [{"id": p.id_parceria, "nome": p.nome, "tipo": p.tipo, "contato": p.contato,
                       "telefone": p.telefone, "status": p.status, "observacoes": p.observacoes}
                      for p in db.query(models.Parceria).order_by(models.Parceria.criado_em.desc())],
        "campanhas": [{"id": c.id_campanha, "nome": c.nome, "canal": c.canal, "objetivo": c.objetivo,
                       "data_inicio": c.data_inicio, "data_fim": c.data_fim, "status": c.status}
                      for c in db.query(models.Campanha).order_by(models.Campanha.data_inicio.desc())],
        "cupons": [{"id": c.id_cupom, "codigo": c.codigo, "desconto_percentual": c.desconto_percentual,
                    "validade": c.validade, "usos": c.usos, "ativo": bool(c.ativo),
                    "valido": bool(c.ativo) and c.validade >= date.today()}
                   for c in db.query(models.Cupom).order_by(models.Cupom.validade.desc())],
    }


@router.post("/marketing/parcerias", status_code=status.HTTP_201_CREATED)
def criar_parceria(dados: schemas.ParceriaCreate, usuario: Usuario = Depends(exige_papel("marketing")),
                   db: Session = Depends(get_db)):
    p = models.Parceria(**dados.model_dump(), criado_em=datetime.now())
    db.add(p)
    db.commit()
    return {"id": p.id_parceria}


@router.patch("/marketing/parcerias/{id_parceria}")
def alterar_parceria(id_parceria: int, dados: schemas.ParceriaCreate,
                     usuario: Usuario = Depends(exige_papel("marketing")), db: Session = Depends(get_db)):
    p = pegar(db, models.Parceria, id_parceria, "Parceria")
    for campo, valor in dados.model_dump().items():
        setattr(p, campo, valor)
    db.commit()
    return {"id": p.id_parceria}


@router.delete("/marketing/parcerias/{id_parceria}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_parceria(id_parceria: int, usuario: Usuario = Depends(exige_papel("marketing")),
                    db: Session = Depends(get_db)):
    db.delete(pegar(db, models.Parceria, id_parceria, "Parceria"))
    db.commit()


@router.post("/marketing/campanhas", status_code=status.HTTP_201_CREATED)
def criar_campanha(dados: schemas.CampanhaCreate, usuario: Usuario = Depends(exige_papel("marketing")),
                   db: Session = Depends(get_db)):
    c = models.Campanha(**dados.model_dump())
    db.add(c)
    db.commit()
    return {"id": c.id_campanha}


@router.delete("/marketing/campanhas/{id_campanha}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_campanha(id_campanha: int, usuario: Usuario = Depends(exige_papel("marketing")),
                    db: Session = Depends(get_db)):
    db.delete(pegar(db, models.Campanha, id_campanha, "Campanha"))
    db.commit()


@router.post("/marketing/cupons", status_code=status.HTTP_201_CREATED)
def criar_cupom(dados: schemas.CupomCreate, usuario: Usuario = Depends(exige_papel("marketing")),
                db: Session = Depends(get_db)):
    codigo = dados.codigo.upper()
    if db.query(models.Cupom).filter_by(codigo=codigo).first():
        raise HTTPException(status_code=409, detail="Já existe um cupom com esse código.")
    c = models.Cupom(codigo=codigo, desconto_percentual=dados.desconto_percentual, validade=dados.validade,
                     ativo=int(dados.ativo))
    db.add(c)
    db.commit()
    return {"id": c.id_cupom, "codigo": c.codigo}


@router.post("/marketing/cupons/{id_cupom}/alternar")
def alternar_cupom(id_cupom: int, usuario: Usuario = Depends(exige_papel("marketing")),
                   db: Session = Depends(get_db)):
    c = pegar(db, models.Cupom, id_cupom, "Cupom")
    c.ativo = 0 if c.ativo else 1
    db.commit()
    return {"id": c.id_cupom, "ativo": bool(c.ativo)}


# =====================================================================
# COMERCIAL
# =====================================================================
@router.get("/comercial")
def comercial(usuario: Usuario = Depends(exige_papel("comercial")), db: Session = Depends(get_db)):
    planos = []
    for p in db.query(models.Plano).order_by(models.Plano.ordem_busca):
        if p.publico == "cuidador":
            assinantes = db.query(models.Cuidador).filter_by(id_plano=p.id_plano, status_cadastro="aprovado").count()
        else:
            assinantes = db.query(models.Paciente).filter_by(status_cadastro="aprovado").count()
        planos.append({"id": p.id_plano, "nome": p.nome, "publico": p.publico, "valor": p.valor,
                       "descricao": p.descricao, "limite_conversas": p.limite_conversas,
                       "pode_iniciar_conversa": bool(p.pode_iniciar_conversa), "destaque": bool(p.destaque),
                       "relatorio": bool(p.relatorio), "assinantes": assinantes,
                       "receita_prevista": round(assinantes * p.valor, 2)})
    return {"planos": planos, "receita_mensal_prevista": round(sum(p["receita_prevista"] for p in planos), 2)}


@router.patch("/comercial/planos/{id_plano}")
def alterar_plano(id_plano: int, dados: schemas.PlanoUpdate, usuario: Usuario = Depends(exige_papel("comercial")),
                  db: Session = Depends(get_db)):
    """O novo preço vale para as próximas mensalidades e já aparece no site."""
    p = pegar(db, models.Plano, id_plano, "Plano")
    if dados.valor is not None:
        p.valor = round(dados.valor, 2)
    if dados.descricao is not None:
        p.descricao = dados.descricao
    if dados.sem_limite:
        p.limite_conversas = None
    elif dados.limite_conversas is not None and p.publico == "cuidador":
        p.limite_conversas = dados.limite_conversas
    db.commit()
    return {"id": p.id_plano, "nome": p.nome, "valor": p.valor, "limite_conversas": p.limite_conversas}


# =====================================================================
# FRONTEND, BACKEND e BANCO
# =====================================================================
def _erros(db: Session, origem: str):
    return [{"id": e.id_erro, "mensagem": e.mensagem, "detalhe": e.detalhe, "pagina": e.pagina,
             "criado_em": e.criado_em}
            for e in db.query(models.LogErro).filter_by(origem=origem)
            .order_by(models.LogErro.criado_em.desc()).limit(50)]


@router.get("/frontend")
def frontend(usuario: Usuario = Depends(exige_papel("frontend")), db: Session = Depends(get_db)):
    paginas = db.query(models.Visita.pagina, func.count()).group_by(models.Visita.pagina) \
        .order_by(func.count().desc()).limit(15).all()
    return {"paginas_mais_acessadas": [{"pagina": p, "visitas": n} for p, n in paginas],
            "visitas_por_dia": _visitas_por_dia(db),
            "total_erros": db.query(models.LogErro).filter_by(origem="site").count(),
            "erros": _erros(db, "site")}


@router.get("/backend")
def backend(usuario: Usuario = Depends(exige_papel("backend")), db: Session = Depends(get_db)):
    est = monitor.estatisticas
    no_ar = int(time.time() - monitor.INICIO)
    rotas = sorted(({"rota": r, "chamadas": v["chamadas"],
                     "tempo_medio_ms": round(v["tempo_total_ms"] / v["chamadas"], 1)}
                    for r, v in est["por_rota"].items()), key=lambda x: -x["chamadas"])[:15]
    return {"status": "online", "no_ar_desde": datetime.fromtimestamp(monitor.INICIO),
            "tempo_no_ar": f"{no_ar // 3600}h {(no_ar % 3600) // 60}min",
            "requisicoes": est["requisicoes"], "erros_500": est["erros_500"],
            "tempo_medio_ms": round(est["tempo_total_ms"] / est["requisicoes"], 1) if est["requisicoes"] else 0,
            "rotas_mais_usadas": rotas,
            "total_erros": db.query(models.LogErro).filter_by(origem="api").count(),
            "erros": _erros(db, "api")}


@router.delete("/logs/{origem}", status_code=status.HTTP_204_NO_CONTENT)
def limpar_erros(origem: str, usuario: Usuario = Depends(exige_papel("frontend", "backend")),
                 db: Session = Depends(get_db)):
    if origem not in ("site", "api"):
        raise HTTPException(status_code=422, detail="Origem deve ser 'site' ou 'api'.")
    if usuario.papel not in ("ADM", {"site": "frontend", "api": "backend"}[origem]):
        raise HTTPException(status_code=403, detail="Você só limpa os erros da sua área.")
    db.query(models.LogErro).filter_by(origem=origem).delete()
    db.commit()


def _tamanho(caminho: Path) -> int:
    return caminho.stat().st_size if caminho.exists() else 0


@router.get("/banco")
def banco(usuario: Usuario = Depends(exige_papel("banco")), db: Session = Depends(get_db)):
    tabelas = []
    for nome in sorted(inspect(engine).get_table_names()):
        tabela = models.Base.metadata.tables.get(nome)
        linhas = db.execute(select(func.count()).select_from(tabela)).scalar() if tabela is not None else None
        tabelas.append({"tabela": nome, "linhas": linhas})
    integridade = db.connection().exec_driver_sql("PRAGMA integrity_check").scalar()
    modo = db.connection().exec_driver_sql("PRAGMA journal_mode").scalar()
    wal = Path(str(ARQUIVO_BANCO) + "-wal")
    return {"arquivo": ARQUIVO_BANCO.name, "tamanho_kb": round(_tamanho(ARQUIVO_BANCO) / 1024, 1),
            "tamanho_wal_kb": round(_tamanho(wal) / 1024, 1), "modo_journal": modo,
            "integridade": integridade, "total_tabelas": len(tabelas),
            "total_linhas": sum(t["linhas"] or 0 for t in tabelas), "tabelas": tabelas}


@router.get("/banco/backup")
def backup(usuario: Usuario = Depends(exige_papel("banco"))):
    """Baixa uma cópia completa e segura do banco (usa a API de backup do SQLite)."""
    with tempfile.TemporaryDirectory() as pasta:
        destino = Path(pasta) / "backup.db"
        origem = sqlite3.connect(ARQUIVO_BANCO)
        copia = sqlite3.connect(destino)
        with copia:
            origem.backup(copia)
        origem.close()
        copia.close()
        conteudo = destino.read_bytes()
    nome = f"cuidado_puro_backup_{datetime.now():%Y-%m-%d_%H%M}.db"
    return Response(content=conteudo, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})
