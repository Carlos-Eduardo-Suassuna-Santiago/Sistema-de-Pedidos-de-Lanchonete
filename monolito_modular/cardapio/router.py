from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from cardapio.service.cardapio_service import CardapioService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> CardapioService:
    return CardapioService(db)


class ItemIn(BaseModel):
    nome: str
    descricao: Optional[str] = ""
    preco: float
    disponivel: Optional[bool] = True


class ItemUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco: Optional[float] = None
    disponivel: Optional[bool] = None


class ItemOut(BaseModel):
    id: int
    nome: str
    descricao: str
    preco: float
    disponivel: bool


@router.post("/", response_model=ItemOut, status_code=201)
def criar_item(dados: ItemIn, svc: CardapioService = Depends(get_service)):
    return svc.criar_item(**dados.model_dump())


@router.get("/", response_model=list[ItemOut])
def listar_itens(svc: CardapioService = Depends(get_service)):
    return svc.listar_itens()


@router.get("/{item_id}", response_model=ItemOut)
def obter_item(item_id: int, svc: CardapioService = Depends(get_service)):
    item = svc.obter_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.patch("/{item_id}", response_model=ItemOut)
def atualizar_item(item_id: int, dados: ItemUpdate, svc: CardapioService = Depends(get_service)):
    item = svc.atualizar_item(item_id, dados.model_dump(exclude_none=True))
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.delete("/{item_id}", status_code=204)
def deletar_item(item_id: int, svc: CardapioService = Depends(get_service)):
    if not svc.deletar_item(item_id):
        raise HTTPException(status_code=404, detail="Item não encontrado")
