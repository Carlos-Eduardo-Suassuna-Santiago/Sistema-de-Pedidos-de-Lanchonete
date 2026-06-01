from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from database import get_db
from pedidos.service.pedido_service import PedidoService
from pedidos.interfaces.pedido_interface import StatusPedidoDTO
from cardapio.service.cardapio_service import CardapioService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> PedidoService:
    cardapio_svc = CardapioService(db)
    return PedidoService(db, cardapio_svc)


class ItemIn(BaseModel):
    item_cardapio_id: int
    quantidade: int = 1


class PedidoIn(BaseModel):
    cliente: str
    itens: list[ItemIn]


class ItemOut(BaseModel):
    id: int
    item_cardapio_id: int
    quantidade: int
    preco_unitario: float


class PedidoOut(BaseModel):
    id: int
    cliente: str
    status: StatusPedidoDTO
    criado_em: datetime
    itens: list[ItemOut]


@router.post("/", response_model=PedidoOut, status_code=201)
def criar_pedido(dados: PedidoIn, svc: PedidoService = Depends(get_service)):
    try:
        return svc.criar_pedido(dados.cliente, [i.model_dump() for i in dados.itens])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[PedidoOut])
def listar_pedidos(svc: PedidoService = Depends(get_service)):
    return svc.listar_pedidos()


@router.get("/{pedido_id}", response_model=PedidoOut)
def obter_pedido(pedido_id: int, svc: PedidoService = Depends(get_service)):
    p = svc.obter_pedido(pedido_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return p


@router.delete("/{pedido_id}", status_code=204)
def cancelar_pedido(pedido_id: int, svc: PedidoService = Depends(get_service)):
    try:
        p = svc.cancelar_pedido(pedido_id)
        if not p:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
