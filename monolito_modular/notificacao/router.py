from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from database import get_db
from notificacao.service.notificacao_service import NotificacaoService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> NotificacaoService:
    return NotificacaoService(db)


class NotificacaoOut(BaseModel):
    id: int
    pedido_id: int
    mensagem: str
    enviada_em: datetime


@router.get("/", response_model=list[NotificacaoOut])
def listar(svc: NotificacaoService = Depends(get_service)):
    return svc.listar()


@router.get("/{pedido_id}", response_model=NotificacaoOut)
def buscar_por_pedido(pedido_id: int, svc: NotificacaoService = Depends(get_service)):
    n = svc.buscar_por_pedido(pedido_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    return n
