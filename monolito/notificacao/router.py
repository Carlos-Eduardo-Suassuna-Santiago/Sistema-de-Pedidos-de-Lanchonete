from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from database import get_db
from models import Notificacao

router = APIRouter()


class NotificacaoOut(BaseModel):
    id: int
    pedido_id: int
    mensagem: str
    enviada_em: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=list[NotificacaoOut])
def listar_notificacoes(db: Session = Depends(get_db)):
    """Lista todas as notificações enviadas à cozinha."""
    return db.query(Notificacao).order_by(Notificacao.enviada_em.desc()).all()


@router.get("/{pedido_id}", response_model=NotificacaoOut)
def obter_notificacao(pedido_id: int, db: Session = Depends(get_db)):
    """Consulta a notificação de um pedido específico."""
    notif = db.query(Notificacao).filter(Notificacao.pedido_id == pedido_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada para este pedido")
    return notif
