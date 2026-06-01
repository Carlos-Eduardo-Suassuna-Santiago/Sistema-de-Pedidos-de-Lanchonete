from sqlalchemy.orm import Session
from pedidos.repository.models import Pedido, ItemPedido, StatusPedido


class PedidoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, cliente: str, itens: list[dict]) -> Pedido:
        pedido = Pedido(cliente=cliente)
        self.db.add(pedido)
        self.db.flush()
        for item in itens:
            self.db.add(ItemPedido(
                pedido_id=pedido.id,
                item_cardapio_id=item["item_cardapio_id"],
                quantidade=item["quantidade"],
                preco_unitario=item["preco_unitario"],
            ))
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def listar(self) -> list[Pedido]:
        return self.db.query(Pedido).all()

    def buscar_por_id(self, pedido_id: int) -> Pedido | None:
        return self.db.query(Pedido).filter(Pedido.id == pedido_id).first()

    def atualizar_status(self, pedido_id: int, status: StatusPedido) -> Pedido | None:
        pedido = self.buscar_por_id(pedido_id)
        if not pedido:
            return None
        pedido.status = status
        self.db.commit()
        self.db.refresh(pedido)
        return pedido

    def cancelar(self, pedido_id: int) -> Pedido | None:
        return self.atualizar_status(pedido_id, StatusPedido.CANCELADO)
