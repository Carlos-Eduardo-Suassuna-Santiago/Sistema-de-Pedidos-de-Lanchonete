from sqlalchemy.orm import Session
from cardapio.repository.models import ItemCardapio


class CardapioRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, nome: str, descricao: str, preco: float, disponivel: bool) -> ItemCardapio:
        item = ItemCardapio(nome=nome, descricao=descricao, preco=preco, disponivel=disponivel)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def listar(self) -> list[ItemCardapio]:
        return self.db.query(ItemCardapio).all()

    def buscar_por_id(self, item_id: int) -> ItemCardapio | None:
        return self.db.query(ItemCardapio).filter(ItemCardapio.id == item_id).first()

    def atualizar(self, item_id: int, dados: dict) -> ItemCardapio | None:
        item = self.buscar_por_id(item_id)
        if not item:
            return None
        for campo, valor in dados.items():
            setattr(item, campo, valor)
        self.db.commit()
        self.db.refresh(item)
        return item

    def deletar(self, item_id: int) -> bool:
        item = self.buscar_por_id(item_id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True
