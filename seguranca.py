# seguranca.py -> senha com hash + "crachá" (token) de quem fez login
#
# Por que hash? Nunca se guarda a senha como texto no banco. Guardamos
# um "embaralhado" que não dá para desfazer. No login, embaralhamos a
# senha digitada do mesmo jeito e comparamos. Usa só a biblioteca padrão
# do Python (hashlib), não precisa instalar nada.
import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
import models

ITERACOES = 100_000


def gerar_hash(senha: str, sal: Optional[str] = None) -> str:
    sal = sal or secrets.token_hex(8)
    calculo = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), ITERACOES)
    return f"pbkdf2${ITERACOES}${sal}${calculo.hex()}"


def conferir_senha(senha: str, guardado: str) -> bool:
    try:
        _, iteracoes, sal, esperado = guardado.split("$")
        calculo = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), int(iteracoes))
        return hmac.compare_digest(calculo.hex(), esperado)
    except ValueError:
        return False


def criar_sessao(db: Session, tipo: str, id_usuario: int) -> str:
    token = secrets.token_hex(32)
    db.add(models.Sessao(token=token, tipo_usuario=tipo, id_usuario=id_usuario))
    db.commit()
    return token


class Usuario:
    """Quem está logado: tipo ('paciente','cuidador','familiar','equipe'),
    id e o registro do banco. Para a equipe, também o papel."""

    def __init__(self, tipo: str, id_usuario: int, registro):
        self.tipo = tipo
        self.id = id_usuario
        self.registro = registro
        self.papel = getattr(registro, "papel", None)
        self.nome = registro.nome


MODELOS = {
    "paciente": (models.Paciente, "id_paciente"),
    "cuidador": (models.Cuidador, "id_cuidador"),
    "familiar": (models.Familiar, "id_familiar"),
    "equipe": (models.EquipeInterna, "id_equipe"),
}


# Lê o cabeçalho "Authorization: Bearer <token>". No Swagger aparece o
# botão "Authorize" (cadeado) para colar o token.
portador = HTTPBearer(auto_error=False, description="Cole aqui o token que o /api/login devolveu")


def usuario_opcional(credencial: Optional[HTTPAuthorizationCredentials] = Depends(portador),
                     db: Session = Depends(get_db)) -> Optional[Usuario]:
    """Descobre quem está logado pelo token. Sem token = None."""
    if credencial is None:
        return None
    sessao = db.get(models.Sessao, credencial.credentials.strip())
    if sessao is None:
        return None
    modelo, _ = MODELOS[sessao.tipo_usuario]
    registro = db.get(modelo, sessao.id_usuario)
    if registro is None:
        return None
    if sessao.tipo_usuario == "equipe" and registro.status != "ativo":
        return None
    return Usuario(sessao.tipo_usuario, sessao.id_usuario, registro)


def usuario_logado(usuario: Optional[Usuario] = Depends(usuario_opcional)) -> Usuario:
    if usuario is None:
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    return usuario


def exige(*tipos: str):
    """Ex.: Depends(exige('paciente')) — só paciente passa."""
    def checar(usuario: Usuario = Depends(usuario_logado)) -> Usuario:
        if usuario.tipo not in tipos:
            raise HTTPException(status_code=403, detail="Seu tipo de usuário não tem acesso a isto.")
        return usuario
    return checar


def exige_papel(*papeis: str):
    """Painel interno. O ADM passa sempre; os outros só no seu papel."""
    def checar(usuario: Usuario = Depends(usuario_logado)) -> Usuario:
        if usuario.tipo != "equipe":
            raise HTTPException(status_code=403, detail="Área exclusiva da equipe interna.")
        if usuario.papel != "ADM" and usuario.papel not in papeis:
            raise HTTPException(status_code=403,
                                detail=f"O papel '{usuario.papel}' não tem acesso a esta parte do painel.")
        return usuario
    return checar
