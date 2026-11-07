# rotas/mensalidades.py -> mensalidade com Pix SIMULADO (QR Code de teste)
#
# Na feira ninguém paga de verdade: o QR Code tem só um texto de teste.
# Num sistema real, a confirmação viria automática do banco, por uma
# integração paga (Mercado Pago, Efí, etc.). Aqui o usuário clica em
# "Confirmar pagamento" e a mensalidade vira 'pago' na hora.
from datetime import date, datetime

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from seguranca import Usuario, exige
from rotas.comum import atualizar_atrasadas, dados_mensalidade, pegar

router = APIRouter(prefix="/api", tags=["6. Mensalidade (Pix simulado)"])

pagante = exige("paciente", "cuidador")


def _minha(db: Session, usuario: Usuario, id_assinatura: int) -> models.Assinatura:
    a = pegar(db, models.Assinatura, id_assinatura, "Mensalidade")
    if a.tipo_usuario != usuario.tipo or a.id_usuario != usuario.id:
        raise HTTPException(status_code=403, detail="Esta mensalidade não é sua.")
    return a


def qrcode_svg(texto: str) -> str:
    imagem = qrcode.make(texto, image_factory=qrcode.image.svg.SvgPathImage, box_size=10)
    return imagem.to_string(encoding="unicode")


@router.get("/mensalidades")
def minhas_mensalidades(usuario: Usuario = Depends(pagante), db: Session = Depends(get_db)):
    atualizar_atrasadas(db)
    lista = db.query(models.Assinatura).filter_by(tipo_usuario=usuario.tipo, id_usuario=usuario.id) \
        .order_by(models.Assinatura.referencia.desc()).all()
    return [dados_mensalidade(a) for a in lista]


@router.post("/mensalidades/{id_assinatura}/pix")
def gerar_pix(id_assinatura: int, dados: schemas.GerarPix, usuario: Usuario = Depends(pagante),
              db: Session = Depends(get_db)):
    """Gera o QR Code (de teste). Aceita cupom de desconto do marketing."""
    a = _minha(db, usuario, id_assinatura)
    if a.status_pagamento == "pago":
        raise HTTPException(status_code=409, detail="Esta mensalidade já está paga.")
    valor = a.plano.valor
    cupom_usado = None
    if dados.cupom:
        cupom = db.query(models.Cupom).filter(models.Cupom.codigo == dados.cupom.strip().upper()).first()
        if cupom is None or not cupom.ativo or cupom.validade < date.today():
            raise HTTPException(status_code=404, detail="Cupom inválido ou vencido.")
        valor = round(valor * (100 - cupom.desconto_percentual) / 100, 2)
        cupom_usado = cupom.codigo
    a.valor, a.codigo_cupom = valor, cupom_usado
    a.codigo_pix = f"PIX-SIMULADO|CUIDADO-PURO|MENSALIDADE-{a.id_assinatura}|{a.referencia}|R${valor:.2f}"
    db.commit()
    return {**dados_mensalidade(a), "codigo_pix": a.codigo_pix, "qrcode_svg": qrcode_svg(a.codigo_pix),
            "aviso": "QR Code de TESTE: não é um Pix de verdade e nenhum banco cobra."}


@router.post("/mensalidades/{id_assinatura}/confirmar")
def confirmar_pagamento(id_assinatura: int, usuario: Usuario = Depends(pagante), db: Session = Depends(get_db)):
    a = _minha(db, usuario, id_assinatura)
    if a.status_pagamento == "pago":
        raise HTTPException(status_code=409, detail="Esta mensalidade já está paga.")
    if not a.codigo_pix:
        raise HTTPException(status_code=409, detail="Gere o QR Code do Pix antes de confirmar.")
    a.status_pagamento, a.data_pagamento = "pago", datetime.now()
    if a.codigo_cupom:
        cupom = db.query(models.Cupom).filter_by(codigo=a.codigo_cupom).first()
        if cupom:
            cupom.usos += 1
    db.commit()
    return {**dados_mensalidade(a), "mensagem": "Pagamento confirmado! Obrigado."}
