from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, relationship
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import httpx
import enum
import os
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pedidos.db")
CARDAPIO_URL = os.getenv("CARDAPIO_URL", "http://localhost:8001")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class StatusPedido(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"
    ENVIADO_COZINHA = "ENVIADO_COZINHA"


class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String, nullable=False)
    status = Column(Enum(StatusPedido), default=StatusPedido.PENDENTE)
    criado_em = Column(DateTime, default=datetime.utcnow)
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")


class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    item_cardapio_id = Column(Integer, nullable=False)
    quantidade = Column(Integer, default=1)
    preco_unitario = Column(Float, nullable=False)
    pedido = relationship("Pedido", back_populates="itens")


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Serviço Pedidos", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Resiliência: retry com backoff ao chamar Cardápio ────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(httpx.RequestError),
)
def buscar_item_cardapio(item_id: int) -> dict:
    """
    Chama o serviço de Cardápio via HTTP com até 3 tentativas.
    Estratégia de resiliência: retry com espera fixa de 1s.
    """
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{CARDAPIO_URL}/cardapio/{item_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


# ── Schemas ──────────────────────────────────────────────────────────────────
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

    class Config:
        from_attributes = True


class PedidoOut(BaseModel):
    id: int
    cliente: str
    status: StatusPedido
    criado_em: datetime
    itens: list[ItemOut]
    valor_total: Optional[float] = None

    class Config:
        from_attributes = True


def pedido_to_out(p: Pedido) -> PedidoOut:
    valor_total = sum(i.preco_unitario * i.quantidade for i in p.itens)
    return PedidoOut(
        id=p.id,
        cliente=p.cliente,
        status=p.status,
        criado_em=p.criado_em,
        itens=p.itens,
        valor_total=valor_total,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "pedidos"}


@app.post("/pedidos/", response_model=PedidoOut, status_code=201)
def criar_pedido(dados: PedidoIn, db: Session = Depends(get_db)):
    if not dados.itens:
        raise HTTPException(status_code=400, detail="Pedido deve ter ao menos um item")

    pedido = Pedido(cliente=dados.cliente)
    db.add(pedido)
    db.flush()

    for item_in in dados.itens:
        try:
            item_cardapio = buscar_item_cardapio(item_in.item_cardapio_id)
        except httpx.RequestError:
            db.rollback()
            raise HTTPException(status_code=503, detail="Serviço de cardápio indisponível")

        if not item_cardapio or not item_cardapio.get("disponivel"):
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Item {item_in.item_cardapio_id} não encontrado ou indisponível",
            )

        db.add(ItemPedido(
            pedido_id=pedido.id,
            item_cardapio_id=item_cardapio["id"],
            quantidade=item_in.quantidade,
            preco_unitario=item_cardapio["preco"],
        ))

    db.commit()
    db.refresh(pedido)
    return pedido_to_out(pedido)


@app.get("/pedidos/", response_model=list[PedidoOut])
def listar_pedidos(db: Session = Depends(get_db)):
    return [pedido_to_out(p) for p in db.query(Pedido).all()]


@app.get("/pedidos/{pedido_id}", response_model=PedidoOut)
def obter_pedido(pedido_id: int, db: Session = Depends(get_db)):
    p = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido_to_out(p)


@app.patch("/pedidos/{pedido_id}/status")
def atualizar_status(pedido_id: int, body: dict, db: Session = Depends(get_db)):
    """Endpoint interno chamado pelo serviço de Pagamento via HTTP."""
    p = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    novo_status = body.get("status")
    if novo_status not in StatusPedido.__members__:
        raise HTTPException(status_code=400, detail="Status inválido")
    p.status = StatusPedido[novo_status]
    db.commit()
    db.refresh(p)
    return pedido_to_out(p)


@app.delete("/pedidos/{pedido_id}", status_code=204)
def cancelar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    p = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if p.status in (StatusPedido.PAGO, StatusPedido.ENVIADO_COZINHA):
        raise HTTPException(status_code=400, detail="Pedido pago não pode ser cancelado")
    p.status = StatusPedido.CANCELADO
    db.commit()
