from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class Notificacao(Base):
    __tablename__ = "notificacao__notificacoes"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, nullable=False, index=True)
    mensagem = Column(String, nullable=False)
    enviada_em = Column(DateTime, default=datetime.utcnow)
