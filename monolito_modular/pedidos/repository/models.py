from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class StatusPedido(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"
    ENVIADO_COZINHA = "ENVIADO_COZINHA"


class Pedido(Base):
    __tablename__ = "pedidos__pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente = Column(String, nullable=False)
    status = Column(Enum(StatusPedido), default=StatusPedido.PENDENTE)
    criado_em = Column(DateTime, default=datetime.utcnow)
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")


class ItemPedido(Base):
    __tablename__ = "pedidos__itens"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos__pedidos.id"), nullable=False)
    item_cardapio_id = Column(Integer, nullable=False)  # Sem FK cruzando módulos!
    quantidade = Column(Integer, default=1)
    preco_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
