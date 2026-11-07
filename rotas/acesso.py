# rotas/acesso.py -> cadastro, login, logout, "quem sou eu" e troca de senha
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from seguranca import (Usuario, conferir_senha, criar_sessao, gerar_hash, usuario_logado)
from rotas.comum import criar_mensalidade, email_em_uso, iniciais, pegar

router = APIRouter(prefix="/api", tags=["1. Acesso e cadastro"])


@router.get("/catalogo")
def catalogo(db: Session = Depends(get_db)):
    """Listas que os formulários de cadastro usam (necessidades, habilidades, planos)."""
    return {
        "necessidades": [{"id": n.id_necessidade, "nome": n.nome_necessidade, "grau": n.grau_dependencia}
                         for n in db.query(models.Necessidade).order_by(models.Necessidade.id_necessidade)],
        "habilidades": [{"id": h.id_habilidade, "nome": h.nome_habilidade,
                         "restrita_tecnico": bool(h.restrita_tecnico)}
                        for h in db.query(models.Habilidade).order_by(models.Habilidade.id_habilidade)],
        "planos": [{"id": p.id_plano, "nome": p.nome, "publico": p.publico, "valor": p.valor,
                    "descricao": p.descricao, "limite_conversas": p.limite_conversas,
                    "pode_iniciar_conversa": bool(p.pode_iniciar_conversa),
                    "destaque": bool(p.destaque), "relatorio": bool(p.relatorio)}
                   for p in db.query(models.Plano).order_by(models.Plano.ordem_busca)],
        "categorias": ["sem registro", "auxiliar de enfermagem", "técnico de enfermagem", "enfermeiro"],
        "origens": ["Google", "Instagram", "Facebook", "Indicação", "Feira", "Parceria", "Outro"],
    }


def _checar_duplicados(db: Session, modelo, cpf: str, email: str):
    if email_em_uso(db, email):
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    if db.query(modelo).filter(modelo.cpf == cpf).first():
        raise HTTPException(status_code=409, detail="Este CPF já está cadastrado.")


@router.post("/cadastro/paciente", status_code=status.HTTP_201_CREATED)
def cadastrar_paciente(dados: schemas.PacienteCreate, db: Session = Depends(get_db)):
    _checar_duplicados(db, models.Paciente, dados.cpf, dados.email)
    necessidades = db.query(models.Necessidade).filter(
        models.Necessidade.id_necessidade.in_(dados.necessidades)).all()
    if len(necessidades) != len(set(dados.necessidades)):
        raise HTTPException(status_code=404, detail="Alguma necessidade escolhida não existe.")

    campos = dados.model_dump(exclude={"senha", "necessidades"})
    paciente = models.Paciente(**campos, senha_hash=gerar_hash(dados.senha), status_cadastro="pendente")
    paciente.necessidades = necessidades
    db.add(paciente)
    db.flush()  # gera o id_paciente antes do commit

    plano = db.query(models.Plano).filter(models.Plano.publico == "paciente").first()
    if plano:
        criar_mensalidade(db, "paciente", paciente.id_paciente, plano)
    db.commit()
    return {"id_paciente": paciente.id_paciente, "nome": paciente.nome, "status_cadastro": "pendente",
            "mensagem": "Cadastro recebido! A equipe vai conferir e aprovar em breve."}


@router.post("/cadastro/cuidador", status_code=status.HTTP_201_CREATED)
def cadastrar_cuidador(dados: schemas.CuidadorCreate, db: Session = Depends(get_db)):
    _checar_duplicados(db, models.Cuidador, dados.cpf, dados.email)
    if dados.categoria_profissional == "sem registro":
        dados.numero_registro_coren = None
    elif not dados.numero_registro_coren:
        raise HTTPException(status_code=422,
                            detail="Para auxiliar, técnico ou enfermeiro, informe o número do COREN.")
    plano = db.get(models.Plano, dados.id_plano)
    if plano is None or plano.publico != "cuidador":
        raise HTTPException(status_code=404, detail="Plano de cuidador não encontrado.")
    habilidades = db.query(models.Habilidade).filter(
        models.Habilidade.id_habilidade.in_(dados.habilidades)).all()
    if len(habilidades) != len(set(dados.habilidades)):
        raise HTTPException(status_code=404, detail="Alguma habilidade escolhida não existe.")
    if dados.categoria_profissional == "sem registro" and any(h.restrita_tecnico for h in habilidades):
        raise HTTPException(status_code=422,
                            detail="Cuidador sem registro não pode marcar habilidades exclusivas de "
                                   "técnico/enfermeiro (injetável, sonda, curativos).")

    campos = dados.model_dump(exclude={"senha", "habilidades"})
    cuidador = models.Cuidador(**campos, senha_hash=gerar_hash(dados.senha), status_cadastro="pendente")
    cuidador.habilidades = habilidades
    db.add(cuidador)
    db.flush()
    criar_mensalidade(db, "cuidador", cuidador.id_cuidador, plano)
    db.commit()
    return {"id_cuidador": cuidador.id_cuidador, "nome": cuidador.nome, "plano": plano.nome,
            "status_cadastro": "pendente",
            "mensagem": "Cadastro recebido! A equipe vai conferir seus documentos e aprovar em breve."}


@router.post("/login")
def login(dados: schemas.Login, db: Session = Depends(get_db)):
    """Login de paciente, cuidador ou familiar. A API descobre sozinha quem é."""
    email = dados.email.strip().lower()
    for tipo, modelo, campo_id in (("paciente", models.Paciente, "id_paciente"),
                                   ("cuidador", models.Cuidador, "id_cuidador"),
                                   ("familiar", models.Familiar, "id_familiar")):
        usuario = db.query(modelo).filter(modelo.email == email).first()
        if usuario and conferir_senha(dados.senha, usuario.senha_hash):
            if getattr(usuario, "status_cadastro", None) == "recusado":
                raise HTTPException(status_code=403,
                                    detail="Seu cadastro foi recusado. Fale com o SAC pelo site.")
            id_usuario = getattr(usuario, campo_id)
            return {"token": criar_sessao(db, tipo, id_usuario), "tipo": tipo, "id": id_usuario,
                    "nome": usuario.nome, "iniciais": iniciais(usuario.nome),
                    "status_cadastro": getattr(usuario, "status_cadastro", "aprovado")}
    if db.query(models.EquipeInterna).filter(models.EquipeInterna.email == email).first():
        raise HTTPException(status_code=401, detail="Este e-mail é da equipe: use o Acesso da equipe.")
    raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")


@router.post("/equipe/login")
def login_equipe(dados: schemas.Login, db: Session = Depends(get_db)):
    """Login da equipe interna. O papel decide o que aparece no painel."""
    membro = db.query(models.EquipeInterna).filter(
        models.EquipeInterna.email == dados.email.strip().lower()).first()
    if membro is None or not conferir_senha(dados.senha, membro.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    if membro.status != "ativo":
        raise HTTPException(status_code=403, detail="Usuário desativado. Fale com o ADM.")
    return {"token": criar_sessao(db, "equipe", membro.id_equipe), "tipo": "equipe",
            "id": membro.id_equipe, "nome": membro.nome, "iniciais": iniciais(membro.nome),
            "papel": membro.papel}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(usuario: Usuario = Depends(usuario_logado), db: Session = Depends(get_db)):
    db.query(models.Sessao).filter(models.Sessao.tipo_usuario == usuario.tipo,
                                   models.Sessao.id_usuario == usuario.id).delete()
    db.commit()


@router.get("/me")
def quem_sou_eu(usuario: Usuario = Depends(usuario_logado)):
    r = usuario.registro
    return {"tipo": usuario.tipo, "id": usuario.id, "nome": usuario.nome, "iniciais": iniciais(usuario.nome),
            "email": r.email, "papel": usuario.papel,
            "status_cadastro": getattr(r, "status_cadastro", "aprovado")}


@router.post("/me/senha")
def trocar_senha(dados: schemas.TrocarSenha, usuario: Usuario = Depends(usuario_logado),
                 db: Session = Depends(get_db)):
    registro = db.merge(usuario.registro)
    if not conferir_senha(dados.senha_atual, registro.senha_hash):
        raise HTTPException(status_code=400, detail="A senha atual não confere.")
    registro.senha_hash = gerar_hash(dados.senha_nova)
    db.commit()
    return {"mensagem": "Senha alterada com sucesso."}
