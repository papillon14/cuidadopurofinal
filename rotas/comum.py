# rotas/comum.py -> funções que várias rotas usam (para não repetir código)
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from seguranca import Usuario

DIA_VENCIMENTO = 10


# ---------------------------------------------------------------------
# Buscar ou devolver 404
# ---------------------------------------------------------------------
def pegar(db: Session, modelo, id_, nome: str):
    registro = db.get(modelo, id_)
    if registro is None:
        raise HTTPException(status_code=404, detail=f"{nome} não encontrado(a).")
    return registro


def email_em_uso(db: Session, email: str) -> bool:
    """Um e-mail só pode existir uma vez no sistema inteiro (login único)."""
    for modelo in (models.Paciente, models.Cuidador, models.Familiar, models.EquipeInterna):
        if db.query(modelo).filter(modelo.email == email).first():
            return True
    return False


def iniciais(nome: str) -> str:
    partes = [p for p in nome.replace("(", " ").split() if p[0].isalpha()]
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()


# ---------------------------------------------------------------------
# Notas e dados públicos do cuidador
# ---------------------------------------------------------------------
def nota_cuidador(db: Session, id_cuidador: int):
    media, qtd = db.query(func.avg(models.Avaliacao.nota), func.count(models.Avaliacao.id_avaliacao)) \
        .filter(models.Avaliacao.id_cuidador == id_cuidador).one()
    return (round(media, 1) if media else None), qtd


def dados_cuidador(db: Session, c: models.Cuidador) -> dict:
    media, qtd = nota_cuidador(db, c.id_cuidador)
    return {
        "id_cuidador": c.id_cuidador,
        "nome": c.nome,
        "iniciais": iniciais(c.nome),
        "categoria_profissional": c.categoria_profissional,
        "numero_registro_coren": c.numero_registro_coren,
        "cidade": c.cidade,
        "descricao": c.descricao,
        "habilidades": [h.nome_habilidade for h in c.habilidades],
        "plano": c.plano.nome,
        "destaque": bool(c.plano.destaque),
        "nota_media": media,
        "qtd_avaliacoes": qtd,
        "status_cadastro": c.status_cadastro,
    }


def idade(nascimento: date) -> int:
    hoje = date.today()
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))


GRAU = {"leve": 1, "moderado": 2, "alto": 3}


def dados_paciente(p: models.Paciente, completo: bool = False) -> dict:
    graus = [n.grau_dependencia for n in p.necessidades]
    dados = {
        "id_paciente": p.id_paciente,
        "nome": p.nome,
        "iniciais": iniciais(p.nome),
        "idade": idade(p.data_nascimento),
        "cidade": p.cidade,
        "necessidades": [n.nome_necessidade for n in p.necessidades],
        "grau_dependencia": max(graus, key=GRAU.get) if graus else None,
        "status_cadastro": p.status_cadastro,
    }
    if completo:  # só para quem tem atendimento combinado
        dados.update({"endereco": p.endereco, "telefone": p.telefone, "cep": p.cep,
                      "nome_responsavel": p.nome_responsavel,
                      "telefone_responsavel": p.telefone_responsavel,
                      "observacoes": p.observacoes})
    return dados


# ---------------------------------------------------------------------
# Conversas e regras do plano
# ---------------------------------------------------------------------
def conversas_abertas(db: Session, id_cuidador: int) -> int:
    return db.query(models.Conversa).filter(
        models.Conversa.id_cuidador == id_cuidador,
        models.Conversa.status.in_(["pendente", "aceita"])).count()


def checar_limite_plano(db: Session, cuidador: models.Cuidador):
    limite = cuidador.plano.limite_conversas
    if limite is not None and conversas_abertas(db, cuidador.id_cuidador) >= limite:
        raise HTTPException(
            status_code=409,
            detail=f"O plano {cuidador.plano.nome} permite até {limite} conversas abertas. "
                   f"Encerre uma conversa ou mude para o plano Padrão.")


def conversa_do_usuario(db: Session, usuario: Usuario, id_conversa: int) -> models.Conversa:
    conversa = pegar(db, models.Conversa, id_conversa, "Conversa")
    if usuario.tipo == "paciente" and conversa.id_paciente == usuario.id:
        return conversa
    if usuario.tipo == "cuidador" and conversa.id_cuidador == usuario.id:
        return conversa
    raise HTTPException(status_code=403, detail="Esta conversa não é sua.")


def mensagem_sistema(db: Session, id_conversa: int, texto: str):
    db.add(models.Mensagem(id_conversa=id_conversa, remetente_tipo="sistema",
                           remetente_id=0, texto=texto, enviado_em=datetime.now()))


# ---------------------------------------------------------------------
# Quem pode ver a saúde do paciente (Modo Pós-Alta)
# ---------------------------------------------------------------------
def ids_pacientes_do_familiar(db: Session, id_familiar: int):
    return [v.id_paciente for v in db.query(models.PacienteFamiliar)
            .filter(models.PacienteFamiliar.id_familiar == id_familiar)]


def cuidador_atende(db: Session, id_cuidador: int, id_paciente: int) -> bool:
    return db.query(models.Conversa).filter(
        models.Conversa.id_cuidador == id_cuidador, models.Conversa.id_paciente == id_paciente,
        models.Conversa.status == "aceita").first() is not None


def checar_acesso_paciente(db: Session, usuario: Usuario, id_paciente: int, escrita: bool = False):
    pegar(db, models.Paciente, id_paciente, "Paciente")
    if usuario.tipo == "paciente" and usuario.id == id_paciente:
        return
    if usuario.tipo == "cuidador" and cuidador_atende(db, usuario.id, id_paciente):
        return
    if usuario.tipo == "familiar" and id_paciente in ids_pacientes_do_familiar(db, usuario.id):
        if escrita:
            raise HTTPException(status_code=403, detail="A central da família é só para acompanhar (leitura).")
        return
    raise HTTPException(status_code=403,
                        detail="Você só vê a saúde de pacientes que você atende ou acompanha.")


# ---------------------------------------------------------------------
# Índice de Bem-Estar e alertas de tendência
# ---------------------------------------------------------------------
def indice(r: models.RegistroDiario) -> float:
    """Média de (10 - dor), sono, alimentação e humor, vezes 10 -> 0 a 100."""
    return round(((10 - r.dor) + r.sono + r.alimentacao + r.humor) / 4 * 10, 1)


def faixa(valor: Optional[float]) -> str:
    if valor is None:
        return "sem dados"
    if valor >= 75:
        return "bom"
    if valor >= 50:
        return "atenção"
    return "alerta"


def pressao_alta(r) -> bool:
    return (r.pressao_sistolica or 0) >= 140 or (r.pressao_diastolica or 0) >= 90


def alertas(registros: list) -> list:
    """Regras simples (não é inteligência artificial). O sistema SINALIZA;
    quem decide é o profissional de saúde."""
    avisos = []
    if not registros:
        return avisos
    ultimo = registros[-1]

    seguidos = 0
    for r in reversed(registros):
        if pressao_alta(r):
            seguidos += 1
        else:
            break
    if seguidos >= 3:
        avisos.append({"nivel": "alto", "titulo": "Pressão alta repetida",
                       "texto": f"Pressão acima de 14x9 em {seguidos} registros seguidos. "
                                "Converse com o médico responsável."})
    elif seguidos >= 1:
        avisos.append({"nivel": "medio", "titulo": "Pressão alta no último registro",
                       "texto": f"Última medida: {ultimo.pressao_sistolica}x{ultimo.pressao_diastolica}."})

    if ultimo.glicemia is not None and (ultimo.glicemia > 180 or ultimo.glicemia < 70):
        avisos.append({"nivel": "alto", "titulo": "Glicemia fora da faixa",
                       "texto": f"Última glicemia: {ultimo.glicemia} mg/dL (faixa comum: 70 a 180)."})

    if ultimo.temperatura is not None and ultimo.temperatura >= 37.8:
        avisos.append({"nivel": "alto", "titulo": "Febre",
                       "texto": f"Temperatura de {ultimo.temperatura} °C no último registro."})

    if len(registros) >= 2 and all(r.dor >= 7 for r in registros[-2:]):
        avisos.append({"nivel": "alto", "titulo": "Dor forte persistente",
                       "texto": "Dor 7 ou mais nos dois últimos registros."})

    if len(registros) >= 6:
        recentes = sum(indice(r) for r in registros[-3:]) / 3
        antes = sum(indice(r) for r in registros[-6:-3]) / 3
        diferenca = round(recentes - antes, 1)
        if diferenca <= -15:
            avisos.append({"nivel": "medio", "titulo": "Bem-estar em queda",
                           "texto": f"O índice caiu {abs(diferenca)} pontos nos últimos 3 registros "
                                    f"(de {round(antes)} para {round(recentes)})."})
        elif diferenca >= 15:
            avisos.append({"nivel": "bom", "titulo": "Bem-estar melhorando",
                           "texto": f"O índice subiu {diferenca} pontos nos últimos 3 registros."})
    return avisos


def resumo_bem_estar(db: Session, id_paciente: int, dias: int = 14) -> dict:
    inicio = datetime.now() - timedelta(days=dias)
    registros = db.query(models.RegistroDiario).filter(
        models.RegistroDiario.id_paciente == id_paciente,
        models.RegistroDiario.data_hora >= inicio).order_by(models.RegistroDiario.data_hora).all()
    atual = indice(registros[-1]) if registros else None
    return {
        "indice_atual": atual,
        "faixa": faixa(atual),
        "serie": [{"data": r.data_hora.strftime("%d/%m"), "indice": indice(r),
                   "pressao": (f"{r.pressao_sistolica}x{r.pressao_diastolica}"
                               if r.pressao_sistolica else None)} for r in registros],
        "alertas": alertas(registros),
        "total_registros": len(registros),
    }


# ---------------------------------------------------------------------
# Mensalidades
# ---------------------------------------------------------------------
def referencia(dia: Optional[date] = None) -> str:
    return (dia or date.today()).strftime("%Y-%m")


def vencimento(ref: str) -> date:
    ano, mes = map(int, ref.split("-"))
    return date(ano, mes, DIA_VENCIMENTO)


def criar_mensalidade(db: Session, tipo: str, id_usuario: int, plano: models.Plano, ref: Optional[str] = None):
    ref = ref or referencia()
    existe = db.query(models.Assinatura).filter_by(tipo_usuario=tipo, id_usuario=id_usuario,
                                                   referencia=ref).first()
    if existe:
        return existe
    venc = vencimento(ref)
    if venc < date.today():           # cadastrou depois do dia 10: vence em 7 dias
        venc = date.today() + timedelta(days=7)
    nova = models.Assinatura(tipo_usuario=tipo, id_usuario=id_usuario, id_plano=plano.id_plano,
                             referencia=ref, valor=plano.valor, status_pagamento="pendente",
                             data_vencimento=venc)
    db.add(nova)
    return nova


def atualizar_atrasadas(db: Session):
    """Pendente com vencimento no passado vira 'atrasado'."""
    db.query(models.Assinatura).filter(
        models.Assinatura.status_pagamento == "pendente",
        models.Assinatura.data_vencimento < date.today()).update({"status_pagamento": "atrasado"})
    db.commit()


def dados_mensalidade(a: models.Assinatura) -> dict:
    return {"id_assinatura": a.id_assinatura, "referencia": a.referencia, "plano": a.plano.nome,
            "valor": a.valor, "valor_cheio": a.plano.valor, "codigo_cupom": a.codigo_cupom,
            "status_pagamento": a.status_pagamento, "data_vencimento": a.data_vencimento,
            "data_pagamento": a.data_pagamento}


# ---------------- MENSALIDADE EM DIA (libera o serviço) ----------------
# Regra: paciente e cuidador só usam o serviço (pedir/aceitar conversa, mandar mensagem,
# propor/confirmar/iniciar atendimento) se a mensalidade DO MÊS estiver PAGA.
# O que NÃO trava: ver o painel, pagar, perfil, SAC, saúde (remédios, consultas, registros),
# concluir um atendimento que já começou e avaliar. Dado de saúde nunca fica preso por dinheiro.
AVISO_PAGAMENTO = ("Mensalidade pendente: pague a mensalidade (menu Mensalidade › Pagar com Pix) "
                   "para liberar conversas e agendamentos.")


def mensalidade_atual(db: Session, tipo: str, id_usuario: int):
    """A do mês atual; se ainda não existir, a mais recente."""
    q = db.query(models.Assinatura).filter_by(tipo_usuario=tipo, id_usuario=id_usuario)
    return q.filter_by(referencia=referencia()).first() or q.order_by(models.Assinatura.referencia.desc()).first()


def esta_em_dia(db: Session, tipo: str, id_usuario: int) -> bool:
    atual = mensalidade_atual(db, tipo, id_usuario)
    return bool(atual and atual.status_pagamento == "pago")


def exigir_em_dia(db: Session, usuario: Usuario):
    """Chame nas rotas que usam o serviço. Erro 402 = 'Payment Required' (pagamento necessário)."""
    if usuario.tipo in ("paciente", "cuidador") and not esta_em_dia(db, usuario.tipo, usuario.id):
        raise HTTPException(status_code=402, detail=AVISO_PAGAMENTO)
