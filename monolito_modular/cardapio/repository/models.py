from sqlalchemy import Column, Integer, String, Float, Boolean
from database import Base


class ItemCardapio(Base):
    # Schema isolado: prefixo "cardapio__" simula schema separado no SQLite
    __tablename__ = "cardapio__itens"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, default="")
    preco = Column(Float, nullable=False)
    disponivel = Column(Boolean, default=True)
