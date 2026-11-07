# rotas/sac.py -> Fale com o SAC (site e dashboards) + contador de visitas e erros do site
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from seguranca import Usuario, exige, usuario_opcional

router = APIRouter(prefix="/api", tags=["7. SAC e monitoramento"])


@router.post("/sac/chamados", status_code=status.HTTP_201_CREATED)
def abrir_chamado(dados: schemas.ChamadoCreate, usuario: Optional[Usuario] = Depends(usuario_opcional),
                  db: Session = Depends(get_db)):
    """Qualquer pessoa pode abrir (página Contato). Se estiver logado, fica ligado ao usuário."""
    autor_tipo = usuario.tipo if usuario and usuario.tipo != "equipe" else "visitante"
    chamado = models.ChamadoSac(autor_tipo=autor_tipo, autor_id=usuario.id if autor_tipo != "visitante" else None,
                                nome=dados.nome, email=dados.email.lower(), assunto=dados.assunto,
                                mensagem=dados.mensagem, criado_em=datetime.now())
    db.add(chamado)
    db.commit()
    return {"id_chamado": chamado.id_chamado, "mensagem": "Recebemos sua mensagem. O SAC vai responder em breve."}


@router.get("/sac/meus-chamados")
def meus_chamados(usuario: Usuario = Depends(exige("paciente", "cuidador", "familiar")),
                  db: Session = Depends(get_db)):
    return [{"id_chamado": c.id_chamado, "assunto": c.assunto, "mensagem": c.mensagem, "status": c.status,
             "resposta": c.resposta, "criado_em": c.criado_em}
            for c in db.query(models.ChamadoSac).filter_by(autor_tipo=usuario.tipo, autor_id=usuario.id)
            .order_by(models.ChamadoSac.criado_em.desc())]


@router.post("/tracking/visita", status_code=status.HTTP_204_NO_CONTENT)
def registrar_visita(dados: schemas.VisitaCreate, db: Session = Depends(get_db)):
    """Cada página do site avisa aqui quando é aberta. Contador REAL (sem número fantasma)."""
    db.add(models.Visita(pagina=dados.pagina, origem=dados.origem, criado_em=datetime.now()))
    db.commit()


@router.post("/logs/erro-site", status_code=status.HTTP_204_NO_CONTENT)
def registrar_erro_site(dados: schemas.ErroSiteCreate, db: Session = Depends(get_db)):
    """Erros de JavaScript do site chegam aqui e aparecem no painel do Frontend."""
    db.add(models.LogErro(origem="site", mensagem=dados.mensagem, detalhe=dados.detalhe,
                          pagina=dados.pagina, criado_em=datetime.now()))
    db.commit()


@router.get("/publico/opinioes")
def opinioes_reais(db: Session = Depends(get_db)):
    """Página Opiniões do site: números e avaliações REAIS do banco (nada inventado)."""
    from sqlalchemy import func
    media, total = db.query(func.avg(models.Avaliacao.nota), func.count(models.Avaliacao.id_avaliacao)).one()
    boas = db.query(models.Avaliacao).filter(models.Avaliacao.nota >= 4, models.Avaliacao.comentario.isnot(None)) \
        .order_by(models.Avaliacao.criado_em.desc()).limit(6).all()
    return {
        "nota_media": round(media, 1) if media else None,
        "total_avaliacoes": total,
        "pacientes": db.query(models.Paciente).filter_by(status_cadastro="aprovado").count(),
        "cuidadores": db.query(models.Cuidador).filter_by(status_cadastro="aprovado").count(),
        "atendimentos": db.query(models.Cuidado).filter_by(status="concluído").count(),
        "avaliacoes": [{"nota": a.nota, "comentario": a.comentario, "autor": a.paciente.nome.split()[0],
                        "cuidador": a.cuidador.nome, "categoria": a.cuidador.categoria_profissional,
                        "data": a.criado_em} for a in boas],
    }
