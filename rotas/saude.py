# rotas/saude.py -> MODO PÓS-ALTA: medicação, consultas, registro diário,
#                   Linha do Tempo, Índice de Bem-Estar e alertas de tendência
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from seguranca import Usuario, exige
from rotas.comum import (checar_acesso_paciente, cuidador_atende, dados_paciente, indice, pegar,
                         resumo_bem_estar)

router = APIRouter(prefix="/api", tags=["5. Saúde (Modo Pós-Alta)"])

quem_acompanha = exige("paciente", "cuidador", "familiar")
quem_edita = exige("paciente", "cuidador")


@router.get("/cuidador/pacientes")
def meus_pacientes(usuario: Usuario = Depends(exige("cuidador")), db: Session = Depends(get_db)):
    """Pacientes com conversa aceita: o cuidador vê a ficha completa e o bem-estar."""
    resultado = []
    for conv in db.query(models.Conversa).filter_by(id_cuidador=usuario.id, status="aceita"):
        resumo = resumo_bem_estar(db, conv.id_paciente)
        resultado.append({**dados_paciente(conv.paciente, completo=True), "id_conversa": conv.id_conversa,
                          "indice_atual": resumo["indice_atual"], "faixa": resumo["faixa"],
                          "alertas": len(resumo["alertas"])})
    return resultado


@router.get("/pacientes/{id_paciente}/ficha")
def ficha(id_paciente: int, usuario: Usuario = Depends(quem_acompanha), db: Session = Depends(get_db)):
    checar_acesso_paciente(db, usuario, id_paciente)
    return dados_paciente(db.get(models.Paciente, id_paciente), completo=True)


# ---------------------------- Medicação ----------------------------
def _med(m: models.Medicacao) -> dict:
    ativa = m.data_fim is None or m.data_fim >= date.today()
    return {"id_medicacao": m.id_medicacao, "nome_medicamento": m.nome_medicamento, "dosagem": m.dosagem,
            "horario": m.horario, "data_inicio": m.data_inicio, "data_fim": m.data_fim,
            "observacoes": m.observacoes, "ativa": ativa}


@router.get("/pacientes/{id_paciente}/medicacoes")
def listar_medicacoes(id_paciente: int, usuario: Usuario = Depends(quem_acompanha), db: Session = Depends(get_db)):
    checar_acesso_paciente(db, usuario, id_paciente)
    lista = [_med(m) for m in db.query(models.Medicacao).filter_by(id_paciente=id_paciente)]
    return sorted(lista, key=lambda m: (not m["ativa"], m["nome_medicamento"]))


@router.post("/pacientes/{id_paciente}/medicacoes", status_code=status.HTTP_201_CREATED)
def criar_medicacao(id_paciente: int, dados: schemas.MedicacaoCreate, usuario: Usuario = Depends(quem_edita),
                    db: Session = Depends(get_db)):
    checar_acesso_paciente(db, usuario, id_paciente, escrita=True)
    if dados.data_fim and dados.data_fim < dados.data_inicio:
        raise HTTPException(status_code=422, detail="A data de fim precisa ser depois do início.")
    m = models.Medicacao(id_paciente=id_paciente, **dados.model_dump())
    db.add(m)
    db.commit()
    return _med(m)


@router.delete("/medicacoes/{id_medicacao}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_medicacao(id_medicacao: int, usuario: Usuario = Depends(quem_edita), db: Session = Depends(get_db)):
    m = pegar(db, models.Medicacao, id_medicacao, "Medicação")
    checar_acesso_paciente(db, usuario, m.id_paciente, escrita=True)
    db.delete(m)
    db.commit()


# ---------------------------- Consultas ----------------------------
def _consulta(c: models.ConsultaMedica) -> dict:
    return {"id_consulta": c.id_consulta, "data_consulta": c.data_consulta, "nome_medico": c.nome_medico,
            "especialidade": c.especialidade, "eh_retorno": bool(c.eh_retorno), "observacoes": c.observacoes,
            "futura": c.data_consulta >= datetime.now()}


@router.get("/pacientes/{id_paciente}/consultas")
def listar_consultas(id_paciente: int, usuario: Usuario = Depends(quem_acompanha), db: Session = Depends(get_db)):
    checar_acesso_paciente(db, usuario, id_paciente)
    return [_consulta(c) for c in db.query(models.ConsultaMedica).filter_by(id_paciente=id_paciente)
            .order_by(models.ConsultaMedica.data_consulta.desc())]


@router.post("/pacientes/{id_paciente}/consultas", status_code=status.HTTP_201_CREATED)
def criar_consulta(id_paciente: int, dados: schemas.ConsultaCreate, usuario: Usuario = Depends(quem_edita),
                   db: Session = Depends(get_db)):
    checar_acesso_paciente(db, usuario, id_paciente, escrita=True)
    c = models.ConsultaMedica(id_paciente=id_paciente, **{**dados.model_dump(),
                                                          "eh_retorno": int(dados.eh_retorno)})
    db.add(c)
    db.commit()
    return _consulta(c)


@router.delete("/consultas/{id_consulta}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_consulta(id_consulta: int, usuario: Usuario = Depends(quem_edita), db: Session = Depends(get_db)):
    c = pegar(db, models.ConsultaMedica, id_consulta, "Consulta")
    checar_acesso_paciente(db, usuario, c.id_paciente, escrita=True)
    db.delete(c)
    db.commit()


# ------------------------- Registro diário -------------------------
def _registro(r: models.RegistroDiario) -> dict:
    return {"id_registro": r.id_registro, "data_hora": r.data_hora,
            "pressao": f"{r.pressao_sistolica}x{r.pressao_diastolica}" if r.pressao_sistolica else None,
            "pressao_sistolica": r.pressao_sistolica, "pressao_diastolica": r.pressao_diastolica,
            "glicemia": r.glicemia, "temperatura": r.temperatura, "dor": r.dor, "sono": r.sono,
            "alimentacao": r.alimentacao, "humor": r.humor, "observacao": r.observacao,
            "indice": indice(r), "cuidador": r.cuidador.nome if r.cuidador else None}


@router.get("/pacientes/{id_paciente}/registros")
def listar_registros(id_paciente: int, usuario: Usuario = Depends(quem_acompanha), db: Session = Depends(get_db)):
    checar_acesso_paciente(db, usuario, id_paciente)
    return [_registro(r) for r in db.query(models.RegistroDiario).filter_by(id_paciente=id_paciente)
            .order_by(models.RegistroDiario.data_hora.desc()).limit(60)]


@router.post("/pacientes/{id_paciente}/registros", status_code=status.HTTP_201_CREATED)
def criar_registro(id_paciente: int, dados: schemas.RegistroCreate, usuario: Usuario = Depends(exige("cuidador")),
                   db: Session = Depends(get_db)):
    """O cuidador anota como o paciente está. Isso alimenta a linha do tempo,
    o índice de bem-estar e os alertas."""
    if not cuidador_atende(db, usuario.id, id_paciente):
        raise HTTPException(status_code=403, detail="Você só registra pacientes que atende (conversa aceita).")
    if (dados.pressao_sistolica is None) != (dados.pressao_diastolica is None):
        raise HTTPException(status_code=422, detail="Informe a pressão completa (ex.: 12 por 8 = 120 e 80).")
    if dados.id_cuidado:
        c = pegar(db, models.Cuidado, dados.id_cuidado, "Atendimento")
        if c.id_paciente != id_paciente or c.id_cuidador != usuario.id:
            raise HTTPException(status_code=403, detail="Este atendimento não é deste paciente.")
    r = models.RegistroDiario(id_paciente=id_paciente, id_cuidador=usuario.id, data_hora=datetime.now(),
                              **dados.model_dump())
    db.add(r)
    db.commit()
    return {"registro": _registro(r), "bem_estar": resumo_bem_estar(db, id_paciente)}


@router.get("/pacientes/{id_paciente}/bem-estar")
def bem_estar(id_paciente: int, dias: int = 14, usuario: Usuario = Depends(quem_acompanha),
              db: Session = Depends(get_db)):
    checar_acesso_paciente(db, usuario, id_paciente)
    return resumo_bem_estar(db, id_paciente, dias=max(1, min(dias, 90)))


@router.get("/pacientes/{id_paciente}/linha-do-tempo")
def linha_do_tempo(id_paciente: int, usuario: Usuario = Depends(quem_acompanha), db: Session = Depends(get_db)):
    """Junta tudo o que aconteceu com o paciente, em ordem (do mais novo para o mais antigo)."""
    checar_acesso_paciente(db, usuario, id_paciente)
    eventos = []
    for r in db.query(models.RegistroDiario).filter_by(id_paciente=id_paciente):
        partes = [f"Bem-estar {indice(r)}"]
        if r.pressao_sistolica:
            partes.append(f"pressão {r.pressao_sistolica}x{r.pressao_diastolica}")
        if r.glicemia:
            partes.append(f"glicemia {r.glicemia}")
        eventos.append({"quando": r.data_hora, "tipo": "registro", "titulo": "Registro diário",
                        "texto": " · ".join(partes) + (f" — {r.observacao}" if r.observacao else ""),
                        "autor": r.cuidador.nome if r.cuidador else None})
    for c in db.query(models.Cuidado).filter(models.Cuidado.id_paciente == id_paciente,
                                             models.Cuidado.status.in_(["agendado", "em andamento", "concluído"])):
        quando = datetime.combine(c.data, datetime.strptime(c.hora_inicio, "%H:%M").time())
        feitas = sum(t.realizado for t in c.tarefas)
        texto = (f"{c.tipo.capitalize()} com {c.cuidador.nome}, {c.hora_inicio}–{c.hora_fim}"
                 f"{' (dia seguinte)' if c.hora_fim < c.hora_inicio else ''}")
        if c.tarefas:
            texto += f" · tarefas {feitas}/{len(c.tarefas)}"
        eventos.append({"quando": quando, "tipo": "atendimento", "titulo": f"Atendimento {c.status}",
                        "texto": texto, "autor": None})
        if c.avaliacao:
            eventos.append({"quando": c.avaliacao.criado_em, "tipo": "avaliacao",
                            "titulo": f"Avaliação: {'★' * c.avaliacao.nota}",
                            "texto": c.avaliacao.comentario or "", "autor": None})
    for c in db.query(models.ConsultaMedica).filter_by(id_paciente=id_paciente):
        eventos.append({"quando": c.data_consulta, "tipo": "consulta",
                        "titulo": "Retorno médico" if c.eh_retorno else "Consulta médica",
                        "texto": f"{c.especialidade} — {c.nome_medico}" + (f" · {c.observacoes}" if c.observacoes else ""),
                        "autor": None})
    for m in db.query(models.Medicacao).filter_by(id_paciente=id_paciente):
        eventos.append({"quando": datetime.combine(m.data_inicio, datetime.min.time()), "tipo": "medicacao",
                        "titulo": "Início de medicação",
                        "texto": f"{m.nome_medicamento} {m.dosagem} ({m.horario})", "autor": None})
    agora = datetime.now()
    for e in eventos:
        e["futuro"] = e["quando"] > agora
    eventos.sort(key=lambda e: e["quando"], reverse=True)
    return eventos
