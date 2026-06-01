from sqlalchemy import Column, Integer, Float, DateTime, Enum
from datetime import datetime
from database import Base
import enum


class StatusPagamento(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


class Pagamento(Base):
    __tablename__ = "pagamento__pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, nullable=False, unique=True, index=True)
    status = Column(Enum(StatusPagamento), default=StatusPagamento.PENDENTE)
    valor = Column(Float, nullable=False)
    processado_em = Column(DateTime, nullable=True)
