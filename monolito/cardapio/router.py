from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import ItemCardapio

router = APIRouter()


class ItemCardapioCreate(BaseModel):
    nome: str
    descricao: Optional[str] = ""
    preco: float
    disponivel: Optional[bool] = True


class ItemCardapioUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    preco: Optional[float] = None
    disponivel: Optional[bool] = None


class ItemCardapioOut(BaseModel):
    id: int
    nome: str
    descricao: str
    preco: float
    disponivel: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=ItemCardapioOut, status_code=201)
def criar_item(item: ItemCardapioCreate, db: Session = Depends(get_db)):
    novo = ItemCardapio(**item.model_dump())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.get("/", response_model=list[ItemCardapioOut])
def listar_itens(db: Session = Depends(get_db)):
    return db.query(ItemCardapio).all()


@router.get("/{item_id}", response_model=ItemCardapioOut)
def obter_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemCardapio).filter(ItemCardapio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.patch("/{item_id}", response_model=ItemCardapioOut)
def atualizar_item(item_id: int, dados: ItemCardapioUpdate, db: Session = Depends(get_db)):
    item = db.query(ItemCardapio).filter(ItemCardapio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(item, campo, valor)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def deletar_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemCardapio).filter(ItemCardapio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
