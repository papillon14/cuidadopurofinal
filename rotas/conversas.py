# rotas/conversas.py -> pedido de conversa (estilo MSN) e chat
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from seguranca import Usuario, exige
from rotas.comum import (checar_limite_plano, conversa_do_usuario, exigir_em_dia, iniciais,
                         mensagem_sistema, pegar)

router = APIRouter(prefix="/api", tags=["3. Conversas e chat"])

so_paciente_ou_cuidador = exige("paciente", "cuidador")


def _resumo(db: Session, conversa: models.Conversa, usuario: Usuario) -> dict:
    if usuario.tipo == "paciente":
        outro, outro_tipo = conversa.cuidador, "cuidador"
        extra = {"categoria": outro.categoria_profissional, "plano": outro.plano.nome,
                 "destaque": bool(outro.plano.destaque)}
    else:
        outro, outro_tipo = conversa.paciente, "paciente"
        extra = {"cidade": outro.cidade}
    ultima = db.query(models.Mensagem).filter_by(id_conversa=conversa.id_conversa) \
        .order_by(models.Mensagem.id_mensagem.desc()).first()
    nao_lidas = db.query(models.Mensagem).filter(
        models.Mensagem.id_conversa == conversa.id_conversa, models.Mensagem.lida == 0,
        models.Mensagem.remetente_tipo == outro_tipo).count()
    return {
        "id_conversa": conversa.id_conversa,
        "status": conversa.status,
        "iniciada_por": conversa.iniciada_por,
        "eu_pedi": conversa.iniciada_por == usuario.tipo,
        "outro": {"tipo": outro_tipo, "id": getattr(outro, f"id_{outro_tipo}"), "nome": outro.nome,
                  "iniciais": iniciais(outro.nome), **extra},
        "ultima_mensagem": ({"texto": ultima.texto, "enviado_em": ultima.enviado_em,
                             "remetente_tipo": ultima.remetente_tipo} if ultima else None),
        "nao_lidas": nao_lidas,
        "criado_em": conversa.criado_em,
    }


@router.get("/conversas")
def minhas_conversas(usuario: Usuario = Depends(so_paciente_ou_cuidador), db: Session = Depends(get_db)):
    campo = models.Conversa.id_paciente if usuario.tipo == "paciente" else models.Conversa.id_cuidador
    conversas = db.query(models.Conversa).filter(campo == usuario.id).all()
    lista = [_resumo(db, c, usuario) for c in conversas]
    ordem = {"pendente": 0, "aceita": 1, "encerrada": 2, "recusada": 3}
    lista.sort(key=lambda x: (ordem[x["status"]],
                              -((x["ultima_mensagem"] or {}).get("enviado_em") or x["criado_em"]).timestamp()))
    return lista


@router.post("/conversas", status_code=status.HTTP_201_CREATED)
def pedir_conversa(dados: schemas.PedidoConversa, usuario: Usuario = Depends(so_paciente_ou_cuidador),
                   db: Session = Depends(get_db)):
    """Manda um pedido de conversa. O outro lado precisa aceitar para o chat abrir."""
    eu = usuario.registro
    if eu.status_cadastro != "aprovado":
        raise HTTPException(status_code=403, detail="Seu cadastro ainda não foi aprovado pela equipe.")
    exigir_em_dia(db, usuario)

    if usuario.tipo == "paciente":
        cuidador = pegar(db, models.Cuidador, dados.id_outro, "Cuidador")
        paciente = eu
        if cuidador.status_cadastro != "aprovado":
            raise HTTPException(status_code=404, detail="Cuidador não encontrado.")
    else:
        cuidador = eu
        paciente = pegar(db, models.Paciente, dados.id_outro, "Paciente")
        if not cuidador.plano.pode_iniciar_conversa:
            raise HTTPException(status_code=403,
                                detail="No plano Básico você recebe pedidos, mas não pode enviar. "
                                       "Mude para o Padrão para chamar pacientes.")
        if paciente.status_cadastro != "aprovado":
            raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    existente = db.query(models.Conversa).filter_by(id_paciente=paciente.id_paciente,
                                                    id_cuidador=cuidador.id_cuidador).first()
    if existente:
        if existente.status in ("pendente", "aceita"):
            raise HTTPException(status_code=409, detail="Vocês já têm uma conversa aberta ou um pedido esperando.")
        checar_limite_plano(db, cuidador)
        existente.status, existente.iniciada_por = "pendente", usuario.tipo   # reabre
        existente.criado_em, existente.respondido_em = datetime.now(), None
        conversa = existente
    else:
        checar_limite_plano(db, cuidador)
        conversa = models.Conversa(id_paciente=paciente.id_paciente, id_cuidador=cuidador.id_cuidador,
                                   iniciada_por=usuario.tipo, status="pendente", criado_em=datetime.now())
        db.add(conversa)
    db.flush()
    mensagem_sistema(db, conversa.id_conversa, f"{eu.nome} enviou um pedido de conversa.")
    db.commit()
    return _resumo(db, conversa, usuario)


@router.post("/conversas/{id_conversa}/responder")
def responder_pedido(id_conversa: int, dados: schemas.Resposta,
                     usuario: Usuario = Depends(so_paciente_ou_cuidador), db: Session = Depends(get_db)):
    conversa = conversa_do_usuario(db, usuario, id_conversa)
    if conversa.status != "pendente":
        raise HTTPException(status_code=409, detail=f"Este pedido já está '{conversa.status}'.")
    if conversa.iniciada_por == usuario.tipo:
        raise HTTPException(status_code=409, detail="Quem responde o pedido é a outra pessoa.")
    if dados.aceitar:                 # recusar pode sempre; aceitar só com a mensalidade em dia
        exigir_em_dia(db, usuario)
    conversa.status = "aceita" if dados.aceitar else "recusada"
    conversa.respondido_em = datetime.now()
    mensagem_sistema(db, id_conversa, f"{usuario.nome} {'aceitou' if dados.aceitar else 'recusou'} o pedido."
                     + (" O chat está liberado!" if dados.aceitar else ""))
    db.commit()
    return _resumo(db, conversa, usuario)


@router.post("/conversas/{id_conversa}/encerrar")
def encerrar_conversa(id_conversa: int, usuario: Usuario = Depends(so_paciente_ou_cuidador),
                      db: Session = Depends(get_db)):
    """Encerra (libera vaga no limite do plano Básico). Pode ser reaberta com novo pedido."""
    conversa = conversa_do_usuario(db, usuario, id_conversa)
    if conversa.status not in ("aceita", "pendente"):
        raise HTTPException(status_code=409, detail="Esta conversa já está encerrada.")
    futuros = db.query(models.Cuidado).filter(
        models.Cuidado.id_conversa == id_conversa,
        models.Cuidado.status.in_(["proposto", "agendado", "em andamento"])).count()
    if futuros:
        raise HTTPException(status_code=409,
                            detail=f"Existem {futuros} atendimento(s) em aberto. Conclua ou cancele antes.")
    conversa.status = "encerrada"
    mensagem_sistema(db, id_conversa, f"{usuario.nome} encerrou a conversa.")
    db.commit()
    return _resumo(db, conversa, usuario)


@router.get("/conversas/{id_conversa}/mensagens")
def ler_mensagens(id_conversa: int, depois_de: Optional[int] = 0,
                  usuario: Usuario = Depends(so_paciente_ou_cuidador), db: Session = Depends(get_db)):
    """O site chama a cada 3 segundos com depois_de=<última id> para buscar só as novas."""
    conversa = conversa_do_usuario(db, usuario, id_conversa)
    mensagens = db.query(models.Mensagem).filter(
        models.Mensagem.id_conversa == id_conversa, models.Mensagem.id_mensagem > (depois_de or 0)) \
        .order_by(models.Mensagem.id_mensagem).all()
    outro_tipo = "cuidador" if usuario.tipo == "paciente" else "paciente"
    marcou = False
    for m in mensagens:
        if m.remetente_tipo == outro_tipo and not m.lida:
            m.lida, marcou = 1, True
    if marcou:
        db.commit()
    return {"status": conversa.status,
            "mensagens": [{"id_mensagem": m.id_mensagem, "remetente_tipo": m.remetente_tipo,
                           "minha": m.remetente_tipo == usuario.tipo, "texto": m.texto,
                           "enviado_em": m.enviado_em} for m in mensagens]}


@router.post("/conversas/{id_conversa}/mensagens", status_code=status.HTTP_201_CREATED)
def enviar_mensagem(id_conversa: int, dados: schemas.MensagemCreate,
                    usuario: Usuario = Depends(so_paciente_ou_cuidador), db: Session = Depends(get_db)):
    conversa = conversa_do_usuario(db, usuario, id_conversa)
    if conversa.status != "aceita":
        raise HTTPException(status_code=403, detail="O chat só libera depois que o pedido for aceito.")
    exigir_em_dia(db, usuario)
    texto = dados.texto.strip()
    if not texto:
        raise HTTPException(status_code=422, detail="A mensagem está vazia.")
    m = models.Mensagem(id_conversa=id_conversa, remetente_tipo=usuario.tipo, remetente_id=usuario.id,
                        texto=texto, enviado_em=datetime.now())
    db.add(m)
    db.commit()
    return {"id_mensagem": m.id_mensagem, "remetente_tipo": m.remetente_tipo, "minha": True,
            "texto": m.texto, "enviado_em": m.enviado_em}
