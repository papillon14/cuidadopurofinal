# rotas/pessoas.py -> perfis, busca de cuidadores/pacientes, planos e central da família
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from seguranca import Usuario, exige, gerar_hash, usuario_opcional
from rotas.comum import (GRAU, conversas_abertas, criar_mensalidade, dados_cuidador, dados_paciente,
                         email_em_uso, ids_pacientes_do_familiar, mensalidade_atual, pegar, referencia,
                         resumo_bem_estar)

router = APIRouter(prefix="/api", tags=["2. Pacientes, cuidadores e família"])


def _conversa_entre(db, id_paciente, id_cuidador):
    return db.query(models.Conversa).filter_by(id_paciente=id_paciente, id_cuidador=id_cuidador).first()


# =====================================================================
# BUSCA DE CUIDADORES (paciente)
# =====================================================================
@router.get("/cuidadores")
def buscar_cuidadores(cidade: Optional[str] = None, categoria: Optional[str] = None,
                      id_habilidade: Optional[int] = None,
                      usuario: Optional[Usuario] = Depends(usuario_opcional),
                      db: Session = Depends(get_db)):
    """Só cuidadores APROVADOS. Ordem: Premium, Padrão, Básico; depois a nota."""
    consulta = db.query(models.Cuidador).join(models.Plano).filter(
        models.Cuidador.status_cadastro == "aprovado")
    if cidade:
        consulta = consulta.filter(models.Cuidador.cidade.ilike(f"%{cidade.strip()}%"))
    if categoria:
        consulta = consulta.filter(models.Cuidador.categoria_profissional == categoria)
    resultado = []
    for c in consulta.all():
        if id_habilidade and id_habilidade not in [h.id_habilidade for h in c.habilidades]:
            continue
        item = dados_cuidador(db, c)
        item["ordem"] = c.plano.ordem_busca
        if usuario and usuario.tipo == "paciente":
            conversa = _conversa_entre(db, usuario.id, c.id_cuidador)
            item["conversa"] = {"id": conversa.id_conversa, "status": conversa.status} if conversa else None
        resultado.append(item)
    resultado.sort(key=lambda x: (-x["ordem"], -(x["nota_media"] or 0), x["nome"]))
    return resultado


@router.get("/cuidadores/{id_cuidador}")
def perfil_cuidador(id_cuidador: int, usuario: Optional[Usuario] = Depends(usuario_opcional),
                    db: Session = Depends(get_db)):
    c = pegar(db, models.Cuidador, id_cuidador, "Cuidador")
    if c.status_cadastro != "aprovado" and not (usuario and usuario.tipo == "equipe"):
        raise HTTPException(status_code=404, detail="Cuidador não encontrado.")
    if usuario and usuario.tipo == "paciente":   # conta a visita ao perfil (relatório Premium)
        c.visualizacoes_perfil += 1
        db.commit()
    dados = dados_cuidador(db, c)
    dados["avaliacoes"] = [{"nota": a.nota, "comentario": a.comentario, "paciente": a.paciente.nome.split()[0],
                            "data": a.criado_em}
                           for a in db.query(models.Avaliacao).filter_by(id_cuidador=id_cuidador)
                           .order_by(models.Avaliacao.criado_em.desc()).limit(10)]
    return dados


# =====================================================================
# PACIENTE
# =====================================================================
@router.get("/paciente/painel")
def painel_paciente(usuario: Usuario = Depends(exige("paciente")), db: Session = Depends(get_db)):
    p = usuario.registro
    hoje = date.today()
    proximos = db.query(models.Cuidado).filter(
        models.Cuidado.id_paciente == p.id_paciente, models.Cuidado.data >= hoje,
        models.Cuidado.status.in_(["proposto", "agendado", "em andamento"])) \
        .order_by(models.Cuidado.data, models.Cuidado.hora_inicio).limit(5).all()
    pendentes_avaliar = db.query(models.Cuidado).filter(
        models.Cuidado.id_paciente == p.id_paciente, models.Cuidado.status == "concluído",
        ~models.Cuidado.avaliacao.has()).count()
    mensalidade = mensalidade_atual(db, "paciente", p.id_paciente)
    return {
        "perfil": {**dados_paciente(p, completo=True), "email": p.email,
                   "id_necessidades": [n.id_necessidade for n in p.necessidades]},
        "proximos": [{"id_cuidado": c.id_cuidado, "data": c.data, "hora_inicio": c.hora_inicio,
                      "hora_fim": c.hora_fim, "tipo": c.tipo, "status": c.status,
                      "com": c.cuidador.nome} for c in proximos],
        "pendentes_avaliar": pendentes_avaliar,
        "bem_estar": resumo_bem_estar(db, p.id_paciente),
        "mensalidade": {"status": mensalidade.status_pagamento, "valor": mensalidade.valor,
                        "id_assinatura": mensalidade.id_assinatura} if mensalidade else None,
        "em_dia": bool(mensalidade and mensalidade.status_pagamento == "pago"),
    }


@router.patch("/paciente/perfil")
def atualizar_paciente(dados: schemas.PacienteUpdate, usuario: Usuario = Depends(exige("paciente")),
                       db: Session = Depends(get_db)):
    p = usuario.registro
    mudancas = dados.model_dump(exclude_unset=True)
    if "necessidades" in mudancas:
        p.necessidades = db.query(models.Necessidade).filter(
            models.Necessidade.id_necessidade.in_(mudancas.pop("necessidades") or [])).all()
    for campo, valor in mudancas.items():
        setattr(p, campo, valor)
    db.commit()
    return dados_paciente(p, completo=True)


# ---------------- Central da família ----------------
@router.get("/paciente/familiares")
def listar_familiares(usuario: Usuario = Depends(exige("paciente")), db: Session = Depends(get_db)):
    return [{"id_familiar": v.id_familiar, "nome": v.familiar.nome, "email": v.familiar.email,
             "telefone": v.familiar.telefone, "parentesco": v.parentesco}
            for v in db.query(models.PacienteFamiliar).filter_by(id_paciente=usuario.id)]


@router.post("/paciente/familiares", status_code=status.HTTP_201_CREATED)
def criar_acesso_familiar(dados: schemas.FamiliarCreate, usuario: Usuario = Depends(exige("paciente")),
                          db: Session = Depends(get_db)):
    """O paciente cria o login de um familiar, que acompanha tudo (só leitura)."""
    if email_em_uso(db, dados.email):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    if db.query(models.Familiar).filter_by(cpf=dados.cpf).first():
        raise HTTPException(status_code=409, detail="Este CPF já está cadastrado.")
    familiar = models.Familiar(nome=dados.nome, cpf=dados.cpf, telefone=dados.telefone,
                               email=dados.email, senha_hash=gerar_hash(dados.senha))
    db.add(familiar)
    db.flush()
    db.add(models.PacienteFamiliar(id_paciente=usuario.id, id_familiar=familiar.id_familiar,
                                   parentesco=dados.parentesco))
    db.commit()
    return {"id_familiar": familiar.id_familiar, "mensagem": f"Acesso criado para {familiar.nome}."}


@router.delete("/paciente/familiares/{id_familiar}", status_code=status.HTTP_204_NO_CONTENT)
def remover_familiar(id_familiar: int, usuario: Usuario = Depends(exige("paciente")),
                     db: Session = Depends(get_db)):
    vinculo = db.query(models.PacienteFamiliar).filter_by(id_paciente=usuario.id,
                                                          id_familiar=id_familiar).first()
    if vinculo is None:
        raise HTTPException(status_code=404, detail="Familiar não encontrado.")
    db.delete(vinculo)
    db.commit()


@router.get("/familiar/painel")
def painel_familiar(usuario: Usuario = Depends(exige("familiar")), db: Session = Depends(get_db)):
    """A família vê os pacientes que acompanha: agenda, saúde e alertas."""
    pacientes = []
    for id_p in ids_pacientes_do_familiar(db, usuario.id):
        p = db.get(models.Paciente, id_p)
        proximos = db.query(models.Cuidado).filter(
            models.Cuidado.id_paciente == id_p, models.Cuidado.data >= date.today(),
            models.Cuidado.status.in_(["agendado", "em andamento", "proposto"])) \
            .order_by(models.Cuidado.data, models.Cuidado.hora_inicio).limit(5).all()
        pacientes.append({
            "perfil": dados_paciente(p, completo=True),
            "proximos": [{"id_cuidado": c.id_cuidado, "data": c.data, "hora_inicio": c.hora_inicio,
                          "hora_fim": c.hora_fim, "tipo": c.tipo, "status": c.status,
                          "com": c.cuidador.nome} for c in proximos],
            "bem_estar": resumo_bem_estar(db, id_p),
        })
    return {"familiar": usuario.nome, "pacientes": pacientes}


# =====================================================================
# CUIDADOR
# =====================================================================
@router.get("/cuidador/painel")
def painel_cuidador(usuario: Usuario = Depends(exige("cuidador")), db: Session = Depends(get_db)):
    c = usuario.registro
    hoje = date.today()
    proximos = db.query(models.Cuidado).filter(
        models.Cuidado.id_cuidador == c.id_cuidador, models.Cuidado.data >= hoje,
        models.Cuidado.status.in_(["proposto", "agendado", "em andamento"])) \
        .order_by(models.Cuidado.data, models.Cuidado.hora_inicio).limit(5).all()
    pedidos = db.query(models.Conversa).filter_by(id_cuidador=c.id_cuidador, status="pendente",
                                                  iniciada_por="paciente").count()
    mensalidade = mensalidade_atual(db, "cuidador", c.id_cuidador)
    dados = dados_cuidador(db, c)
    dados.update({"telefone": c.telefone, "email": c.email, "cep": c.cep,
                  "id_habilidades": [h.id_habilidade for h in c.habilidades]})
    return {
        "perfil": dados,
        "plano": {"id": c.plano.id_plano, "nome": c.plano.nome, "valor": c.plano.valor,
                  "descricao": c.plano.descricao, "limite_conversas": c.plano.limite_conversas,
                  "pode_iniciar_conversa": bool(c.plano.pode_iniciar_conversa),
                  "destaque": bool(c.plano.destaque), "relatorio": bool(c.plano.relatorio),
                  "conversas_abertas": conversas_abertas(db, c.id_cuidador)},
        "pedidos_pendentes": pedidos,
        "proximos": [{"id_cuidado": x.id_cuidado, "data": x.data, "hora_inicio": x.hora_inicio,
                      "hora_fim": x.hora_fim, "tipo": x.tipo, "status": x.status,
                      "com": x.paciente.nome, "endereco": x.paciente.endereco} for x in proximos],
        "concluidos_mes": db.query(models.Cuidado).filter(
            models.Cuidado.id_cuidador == c.id_cuidador, models.Cuidado.status == "concluído",
            models.Cuidado.data >= hoje.replace(day=1)).count(),
        "mensalidade": {"status": mensalidade.status_pagamento, "valor": mensalidade.valor,
                        "id_assinatura": mensalidade.id_assinatura} if mensalidade else None,
        "em_dia": bool(mensalidade and mensalidade.status_pagamento == "pago"),
    }


@router.patch("/cuidador/perfil")
def atualizar_cuidador(dados: schemas.CuidadorUpdate, usuario: Usuario = Depends(exige("cuidador")),
                       db: Session = Depends(get_db)):
    c = usuario.registro
    mudancas = dados.model_dump(exclude_unset=True)
    if "habilidades" in mudancas:
        habs = db.query(models.Habilidade).filter(
            models.Habilidade.id_habilidade.in_(mudancas.pop("habilidades") or [])).all()
        if c.categoria_profissional == "sem registro" and any(h.restrita_tecnico for h in habs):
            raise HTTPException(status_code=422, detail="Habilidade exclusiva de técnico/enfermeiro.")
        c.habilidades = habs
    for campo, valor in mudancas.items():
        setattr(c, campo, valor)
    db.commit()
    return dados_cuidador(db, c)


@router.patch("/cuidador/plano")
def trocar_plano(dados: schemas.TrocarPlano, usuario: Usuario = Depends(exige("cuidador")),
                 db: Session = Depends(get_db)):
    """Muda o plano na hora. A mensalidade do mês, se ainda não foi paga, passa a ter o novo valor."""
    c = usuario.registro
    plano = db.get(models.Plano, dados.id_plano)
    if plano is None or plano.publico != "cuidador":
        raise HTTPException(status_code=404, detail="Plano de cuidador não encontrado.")
    if plano.limite_conversas is not None and conversas_abertas(db, c.id_cuidador) > plano.limite_conversas:
        raise HTTPException(status_code=409,
                            detail=f"Você tem mais de {plano.limite_conversas} conversas abertas. "
                                   "Encerre algumas antes de mudar para esse plano.")
    c.id_plano = plano.id_plano
    mensalidade = mensalidade_atual(db, "cuidador", c.id_cuidador)
    if mensalidade and mensalidade.status_pagamento != "pago":
        mensalidade.id_plano, mensalidade.valor, mensalidade.codigo_cupom = plano.id_plano, plano.valor, None
        mensalidade.codigo_pix = None
    elif mensalidade is None:
        criar_mensalidade(db, "cuidador", c.id_cuidador, plano)
    db.commit()
    return {"mensagem": f"Plano alterado para {plano.nome}.", "plano": plano.nome}


@router.get("/cuidador/relatorio")
def relatorio_premium(usuario: Usuario = Depends(exige("cuidador")), db: Session = Depends(get_db)):
    c = usuario.registro
    if not c.plano.relatorio:
        raise HTTPException(status_code=403, detail="O relatório de visitas é exclusivo do plano Premium.")
    posicao = 1 + sum(1 for x in buscar_cuidadores(db=db, usuario=None)
                      if x["id_cuidador"] != c.id_cuidador and x["ordem"] > c.plano.ordem_busca)
    return {
        "visualizacoes_perfil": c.visualizacoes_perfil,
        "pedidos_recebidos": db.query(models.Conversa).filter_by(id_cuidador=c.id_cuidador,
                                                                 iniciada_por="paciente").count(),
        "conversas_aceitas": db.query(models.Conversa).filter_by(id_cuidador=c.id_cuidador,
                                                                 status="aceita").count(),
        "atendimentos_concluidos": db.query(models.Cuidado).filter_by(id_cuidador=c.id_cuidador,
                                                                      status="concluído").count(),
        "posicao_na_busca": posicao,
    }


@router.get("/pacientes")
def buscar_pacientes(cidade: Optional[str] = None, usuario: Usuario = Depends(exige("cuidador")),
                     db: Session = Depends(get_db)):
    """Cuidador Padrão e Premium podem procurar pacientes e mandar pedido de conversa."""
    if not usuario.registro.plano.pode_iniciar_conversa:
        raise HTTPException(status_code=403,
                            detail="Procurar pacientes é liberado a partir do plano Padrão.")
    consulta = db.query(models.Paciente).filter(models.Paciente.status_cadastro == "aprovado")
    if cidade:
        consulta = consulta.filter(models.Paciente.cidade.ilike(f"%{cidade.strip()}%"))
    resultado = []
    for p in consulta.order_by(models.Paciente.data_criacao.desc()):
        item = dados_paciente(p)
        conversa = _conversa_entre(db, p.id_paciente, usuario.id)
        item["conversa"] = {"id": conversa.id_conversa, "status": conversa.status} if conversa else None
        resultado.append(item)
    resultado.sort(key=lambda x: -GRAU.get(x["grau_dependencia"] or "leve", 0))
    return resultado
