from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from pydantic import BaseModel
from typing import Optional
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cardapio.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class ItemCardapio(Base):
    __tablename__ = "itens"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, default="")
    preco = Column(Float, nullable=False)
    disponivel = Column(Boolean, default=True)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Serviço Cardápio", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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

    class Config:
        from_attributes = True


@app.get("/health")
def health():
    return {"status": "ok", "service": "cardapio"}


@app.post("/cardapio/", response_model=ItemOut, status_code=201)
def criar(dados: ItemIn, db: Session = Depends(get_db)):
    item = ItemCardapio(**dados.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/cardapio/", response_model=list[ItemOut])
def listar(db: Session = Depends(get_db)):
    return db.query(ItemCardapio).all()


@app.get("/cardapio/{item_id}", response_model=ItemOut)
def obter(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemCardapio).filter(ItemCardapio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@app.patch("/cardapio/{item_id}", response_model=ItemOut)
def atualizar(item_id: int, dados: ItemUpdate, db: Session = Depends(get_db)):
    item = db.query(ItemCardapio).filter(ItemCardapio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(item, campo, valor)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/cardapio/{item_id}", status_code=204)
def deletar(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItemCardapio).filter(ItemCardapio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
