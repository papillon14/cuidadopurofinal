# rotas/agenda.py -> agendamento combinado no chat, checklist e avaliação
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from seguranca import Usuario, exige
from rotas.comum import (conversa_do_usuario, exigir_em_dia, ids_pacientes_do_familiar, mensagem_sistema,
                         pegar)

router = APIRouter(prefix="/api", tags=["4. Agenda e avaliação"])

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MAX_REPETICOES = 60


def dados_cuidado(c: models.Cuidado, usuario: Optional[Usuario] = None) -> dict:
    dados = {
        "id_cuidado": c.id_cuidado, "id_conversa": c.id_conversa, "tipo": c.tipo,
        "data": c.data, "hora_inicio": c.hora_inicio, "hora_fim": c.hora_fim,
        "observacoes": c.observacoes, "status": c.status, "proposto_por": c.proposto_por,
        "grupo_repeticao": c.grupo_repeticao,
        "paciente": {"id": c.id_paciente, "nome": c.paciente.nome, "endereco": c.paciente.endereco,
                     "telefone": c.paciente.telefone},
        "cuidador": {"id": c.id_cuidador, "nome": c.cuidador.nome,
                     "categoria": c.cuidador.categoria_profissional},
        "tarefas": [{"id": t.id_cuidado_tarefa, "descricao": t.descricao, "realizado": bool(t.realizado)}
                    for t in c.tarefas],
        "avaliacao": ({"nota": c.avaliacao.nota, "comentario": c.avaliacao.comentario}
                      if c.avaliacao else None),
    }
    if usuario:
        dados["posso_confirmar"] = c.status == "proposto" and c.proposto_por != usuario.tipo \
            and usuario.tipo in ("paciente", "cuidador")
        dados["posso_avaliar"] = usuario.tipo == "paciente" and c.status == "concluído" and not c.avaliacao
    return dados


def cuidado_do_usuario(db: Session, usuario: Usuario, id_cuidado: int) -> models.Cuidado:
    c = pegar(db, models.Cuidado, id_cuidado, "Atendimento")
    if (usuario.tipo == "paciente" and c.id_paciente == usuario.id) or \
       (usuario.tipo == "cuidador" and c.id_cuidador == usuario.id):
        return c
    raise HTTPException(status_code=403, detail="Este atendimento não é seu.")


@router.get("/agenda")
def minha_agenda(periodo: str = "todos", usuario: Usuario = Depends(exige("paciente", "cuidador", "familiar")),
                 db: Session = Depends(get_db)):
    """periodo: 'futuros', 'passados' ou 'todos'."""
    q = db.query(models.Cuidado)
    if usuario.tipo == "paciente":
        q = q.filter(models.Cuidado.id_paciente == usuario.id)
    elif usuario.tipo == "cuidador":
        q = q.filter(models.Cuidado.id_cuidador == usuario.id)
    else:
        q = q.filter(models.Cuidado.id_paciente.in_(ids_pacientes_do_familiar(db, usuario.id)))
    hoje = date.today()
    if periodo == "futuros":
        q = q.filter(models.Cuidado.data >= hoje)
    elif periodo == "passados":
        q = q.filter(models.Cuidado.data < hoje)
    itens = q.order_by(models.Cuidado.data, models.Cuidado.hora_inicio).all()
    return [dados_cuidado(c, usuario) for c in itens]


def _datas(dados: schemas.AgendamentoCreate):
    if not dados.repetir_dias:
        return [dados.data]
    if not dados.repetir_ate or dados.repetir_ate < dados.data:
        raise HTTPException(status_code=422, detail="Para repetir, informe até quando (data final).")
    if any(d not in range(7) for d in dados.repetir_dias):
        raise HTTPException(status_code=422, detail="Dias da semana vão de 0 (segunda) a 6 (domingo).")
    datas, dia = [], dados.data
    while dia <= dados.repetir_ate:
        if dia.weekday() in dados.repetir_dias:
            datas.append(dia)
        dia += timedelta(days=1)
    if not datas:
        raise HTTPException(status_code=422, detail="Nenhum dia escolhido cai dentro do período.")
    if len(datas) > MAX_REPETICOES:
        raise HTTPException(status_code=422, detail=f"No máximo {MAX_REPETICOES} atendimentos por escala.")
    return datas


@router.post("/conversas/{id_conversa}/agendamentos", status_code=status.HTTP_201_CREATED)
def propor_agendamento(id_conversa: int, dados: schemas.AgendamentoCreate,
                       usuario: Usuario = Depends(exige("paciente", "cuidador")), db: Session = Depends(get_db)):
    """Propõe dia, horário e tipo. Com repetir_dias cria a escala inteira de uma vez.
    O outro lado confirma em /agendamentos/{id}/responder."""
    conversa = conversa_do_usuario(db, usuario, id_conversa)
    if conversa.status != "aceita":
        raise HTTPException(status_code=403, detail="Primeiro o pedido de conversa precisa ser aceito.")
    exigir_em_dia(db, usuario)
    if dados.data < date.today():
        raise HTTPException(status_code=422, detail="A data não pode ser no passado.")
    datas = _datas(dados)
    grupo = uuid.uuid4().hex[:12] if len(datas) > 1 else None
    criados = []
    for dia in datas:
        c = models.Cuidado(id_conversa=id_conversa, id_cuidador=conversa.id_cuidador,
                           id_paciente=conversa.id_paciente, proposto_por=usuario.tipo, tipo=dados.tipo,
                           data=dia, hora_inicio=dados.hora_inicio, hora_fim=dados.hora_fim,
                           observacoes=dados.observacoes, status="proposto", grupo_repeticao=grupo,
                           criado_em=datetime.now())
        c.tarefas = [models.CuidadoTarefa(descricao=t.strip()[:150]) for t in dados.tarefas if t.strip()]
        db.add(c)
        criados.append(c)
    texto = (f"📅 {usuario.nome} propôs {dados.tipo} em {dados.data.strftime('%d/%m/%Y')}, "
             f"das {dados.hora_inicio} às {dados.hora_fim}"
             f"{' do dia seguinte' if dados.hora_fim < dados.hora_inicio else ''}.")
    if grupo:
        dias = ", ".join(DIAS[d] for d in sorted(dados.repetir_dias))
        texto += f" Repete ({dias}) até {dados.repetir_ate.strftime('%d/%m/%Y')}: {len(datas)} atendimentos."
    mensagem_sistema(db, id_conversa, texto + " Aguardando confirmação.")
    db.commit()
    return {"quantidade": len(criados), "grupo_repeticao": grupo,
            "agendamentos": [dados_cuidado(c, usuario) for c in criados]}


def _grupo(db: Session, c: models.Cuidado):
    if c.grupo_repeticao:
        return db.query(models.Cuidado).filter_by(grupo_repeticao=c.grupo_repeticao, status="proposto").all()
    return [c]


@router.post("/agendamentos/{id_cuidado}/responder")
def responder_proposta(id_cuidado: int, dados: schemas.Resposta,
                       usuario: Usuario = Depends(exige("paciente", "cuidador")), db: Session = Depends(get_db)):
    """Confirma ou recusa. Se for escala, vale para todos os dias dela."""
    c = cuidado_do_usuario(db, usuario, id_cuidado)
    if c.status != "proposto":
        raise HTTPException(status_code=409, detail=f"Este agendamento já está '{c.status}'.")
    if c.proposto_por == usuario.tipo:
        raise HTTPException(status_code=409, detail="Quem confirma é a outra pessoa.")
    if dados.aceitar:                 # recusar pode sempre; confirmar só com a mensalidade em dia
        exigir_em_dia(db, usuario)
    itens = _grupo(db, c)
    for item in itens:
        item.status = "agendado" if dados.aceitar else "recusado"
    mensagem_sistema(db, c.id_conversa,
                     f"{'✅' if dados.aceitar else '❌'} {usuario.nome} "
                     f"{'confirmou' if dados.aceitar else 'recusou'} {len(itens)} atendimento(s).")
    db.commit()
    return {"status": "agendado" if dados.aceitar else "recusado", "quantidade": len(itens)}


@router.post("/agendamentos/{id_cuidado}/iniciar")
def iniciar(id_cuidado: int, usuario: Usuario = Depends(exige("cuidador")), db: Session = Depends(get_db)):
    c = cuidado_do_usuario(db, usuario, id_cuidado)
    if c.status != "agendado":
        raise HTTPException(status_code=409, detail="Só dá para iniciar um atendimento confirmado (agendado).")
    exigir_em_dia(db, usuario)
    c.status = "em andamento"
    mensagem_sistema(db, c.id_conversa, f"▶️ {usuario.nome} iniciou o atendimento de {c.data.strftime('%d/%m')}.")
    db.commit()
    return dados_cuidado(c, usuario)


@router.post("/agendamentos/{id_cuidado}/concluir")
def concluir(id_cuidado: int, usuario: Usuario = Depends(exige("cuidador")), db: Session = Depends(get_db)):
    """O cuidador conclui quando quiser (não precisa esperar o horário: bom para testar)."""
    c = cuidado_do_usuario(db, usuario, id_cuidado)
    if c.status not in ("agendado", "em andamento"):
        raise HTTPException(status_code=409, detail="Só dá para concluir um atendimento agendado ou em andamento.")
    c.status = "concluído"
    mensagem_sistema(db, c.id_conversa,
                     f"✔️ Atendimento de {c.data.strftime('%d/%m')} concluído. O paciente já pode avaliar.")
    db.commit()
    return dados_cuidado(c, usuario)


@router.post("/agendamentos/{id_cuidado}/cancelar")
def cancelar(id_cuidado: int, usuario: Usuario = Depends(exige("paciente", "cuidador")),
             db: Session = Depends(get_db)):
    c = cuidado_do_usuario(db, usuario, id_cuidado)
    if c.status not in ("proposto", "agendado"):
        raise HTTPException(status_code=409, detail=f"Não dá para cancelar um atendimento '{c.status}'.")
    c.status = "cancelado"
    mensagem_sistema(db, c.id_conversa, f"🚫 {usuario.nome} cancelou o atendimento de {c.data.strftime('%d/%m')}.")
    db.commit()
    return dados_cuidado(c, usuario)


@router.patch("/agendamentos/{id_cuidado}/tarefas/{id_tarefa}")
def marcar_tarefa(id_cuidado: int, id_tarefa: int, dados: schemas.Tarefa,
                  usuario: Usuario = Depends(exige("cuidador")), db: Session = Depends(get_db)):
    c = cuidado_do_usuario(db, usuario, id_cuidado)
    tarefa = next((t for t in c.tarefas if t.id_cuidado_tarefa == id_tarefa), None)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada neste atendimento.")
    tarefa.realizado = 1 if dados.realizado else 0
    db.commit()
    return dados_cuidado(c, usuario)


@router.post("/agendamentos/{id_cuidado}/avaliacao", status_code=status.HTTP_201_CREATED)
def avaliar(id_cuidado: int, dados: schemas.AvaliacaoCreate, usuario: Usuario = Depends(exige("paciente")),
            db: Session = Depends(get_db)):
    """Só atendimento concluído, uma vez. Nota 1 ou 2 vai para o painel do SAC."""
    c = cuidado_do_usuario(db, usuario, id_cuidado)
    if c.status != "concluído":
        raise HTTPException(status_code=409, detail="Só dá para avaliar depois que o atendimento for concluído.")
    if c.avaliacao:
        raise HTTPException(status_code=409, detail="Este atendimento já foi avaliado.")
    avaliacao = models.Avaliacao(id_cuidado=id_cuidado, id_paciente=c.id_paciente, id_cuidador=c.id_cuidador,
                                 nota=dados.nota, comentario=(dados.comentario or "").strip() or None,
                                 status_sac="nova" if dados.nota <= 2 else "ok", criado_em=datetime.now())
    db.add(avaliacao)
    mensagem_sistema(db, c.id_conversa, f"⭐ {usuario.nome} avaliou o atendimento com nota {dados.nota}.")
    db.commit()
    return {"mensagem": "Obrigado pela avaliação!", "nota": dados.nota,
            "foi_para_sac": dados.nota <= 2}
