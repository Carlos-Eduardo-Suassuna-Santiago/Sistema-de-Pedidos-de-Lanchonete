from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum


class StatusPedido(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"
    ENVIADO_COZINHA = "ENVIADO_COZINHA"


class StatusPagamento(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


# ---------- Cardápio ----------
class ItemCardapio(Base):
    __tablename__ = "itens_cardapio"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, default="")
    preco = Column(Float, nullable=False)
    disponivel = Column(Boolean, default=True)


# ---------- Pedidos ----------
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
    item_cardapio_id = Column(Integer, ForeignKey("itens_cardapio.id"), nullable=False)
    quantidade = Column(Integer, default=1)
    preco_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    item_cardapio = relationship("ItemCardapio")


# ---------- Pagamento ----------
class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False, unique=True)
    status = Column(Enum(StatusPagamento), default=StatusPagamento.PENDENTE)
    valor = Column(Float, nullable=False)
    processado_em = Column(DateTime, nullable=True)

    pedido = relationship("Pedido")


# ---------- Notificação ----------
class Notificacao(Base):
    __tablename__ = "notificacoes"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    mensagem = Column(String, nullable=False)
    enviada_em = Column(DateTime, default=datetime.utcnow)

    pedido = relationship("Pedido")
