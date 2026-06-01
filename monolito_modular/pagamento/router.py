from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from database import get_db
from pagamento.service.pagamento_service import PagamentoService
from pagamento.interfaces.pagamento_interface import StatusPagamentoDTO
from pedidos.service.pedido_service import PedidoService
from notificacao.service.notificacao_service import NotificacaoService
from cardapio.service.cardapio_service import CardapioService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> PagamentoService:
    # Injeção de dependências: monta o grafo de serviços aqui
    cardapio_svc = CardapioService(db)
    pedido_svc = PedidoService(db, cardapio_svc)
    notificacao_svc = NotificacaoService(db)
    return PagamentoService(db, pedido_svc, notificacao_svc)


class PagamentoIn(BaseModel):
    pedido_id: int


class PagamentoOut(BaseModel):
    id: int
    pedido_id: int
    status: StatusPagamentoDTO
    valor: float
    processado_em: datetime | None


@router.post("/processar", response_model=PagamentoOut, status_code=201)
def processar(dados: PagamentoIn, svc: PagamentoService = Depends(get_service)):
    try:
        return svc.processar(dados.pedido_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{pedido_id}/status", response_model=PagamentoOut)
def consultar_status(pedido_id: int, svc: PagamentoService = Depends(get_service)):
    p = svc.consultar_status(pedido_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return p
