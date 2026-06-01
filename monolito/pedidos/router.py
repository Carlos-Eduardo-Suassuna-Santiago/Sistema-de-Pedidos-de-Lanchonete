from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from models import Pedido, ItemPedido, ItemCardapio, StatusPedido

router = APIRouter()


class ItemPedidoIn(BaseModel):
    item_cardapio_id: int
    quantidade: int = 1


class PedidoCreate(BaseModel):
    cliente: str
    itens: list[ItemPedidoIn]


class ItemPedidoOut(BaseModel):
    id: int
    item_cardapio_id: int
    quantidade: int
    preco_unitario: float

    class Config:
        from_attributes = True


class PedidoOut(BaseModel):
    id: int
    cliente: str
    status: StatusPedido
    criado_em: datetime
    itens: list[ItemPedidoOut]

    class Config:
        from_attributes = True


@router.post("/", response_model=PedidoOut, status_code=201)
def criar_pedido(dados: PedidoCreate, db: Session = Depends(get_db)):
    if not dados.itens:
        raise HTTPException(status_code=400, detail="O pedido deve ter ao menos um item")

    pedido = Pedido(cliente=dados.cliente)
    db.add(pedido)
    db.flush()  # gera o ID do pedido antes de adicionar itens

    for item_in in dados.itens:
        item_cardapio = db.query(ItemCardapio).filter(
            ItemCardapio.id == item_in.item_cardapio_id,
            ItemCardapio.disponivel == True
        ).first()
        if not item_cardapio:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Item {item_in.item_cardapio_id} não encontrado ou indisponível"
            )
        item_pedido = ItemPedido(
            pedido_id=pedido.id,
            item_cardapio_id=item_cardapio.id,
            quantidade=item_in.quantidade,
            preco_unitario=item_cardapio.preco,
        )
        db.add(item_pedido)

    db.commit()
    db.refresh(pedido)
    return pedido


@router.get("/", response_model=list[PedidoOut])
def listar_pedidos(db: Session = Depends(get_db)):
    return db.query(Pedido).all()


@router.get("/{pedido_id}", response_model=PedidoOut)
def obter_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido


@router.delete("/{pedido_id}", status_code=204)
def cancelar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if pedido.status == StatusPedido.PAGO:
        raise HTTPException(status_code=400, detail="Pedido já pago não pode ser cancelado")
    pedido.status = StatusPedido.CANCELADO
    db.commit()
