from sqlalchemy.orm import Session
from pedidos.interfaces.pedido_interface import (
    PedidoServiceInterface, PedidoDTO, ItemPedidoDTO, StatusPedidoDTO
)
from pedidos.repository.pedido_repository import PedidoRepository
from pedidos.repository.models import StatusPedido
from cardapio.interfaces.cardapio_interface import CardapioServiceInterface


def _to_dto(pedido) -> PedidoDTO:
    return PedidoDTO(
        id=pedido.id,
        cliente=pedido.cliente,
        status=StatusPedidoDTO(pedido.status.value),
        criado_em=pedido.criado_em,
        itens=[
            ItemPedidoDTO(
                id=i.id,
                item_cardapio_id=i.item_cardapio_id,
                quantidade=i.quantidade,
                preco_unitario=i.preco_unitario,
            )
            for i in pedido.itens
        ],
    )


class PedidoService(PedidoServiceInterface):
    def __init__(self, db: Session, cardapio_svc: CardapioServiceInterface):
        self._repo = PedidoRepository(db)
        # Dependência do módulo Cardápio via INTERFACE — nunca importando seu repositório
        self._cardapio = cardapio_svc

    # ── Interface pública (usada por outros módulos) ─────────────────────────

    def obter_pedido(self, pedido_id: int) -> PedidoDTO | None:
        p = self._repo.buscar_por_id(pedido_id)
        return _to_dto(p) if p else None

    def marcar_como_pago(self, pedido_id: int) -> PedidoDTO:
        p = self._repo.atualizar_status(pedido_id, StatusPedido.PAGO)
        if not p:
            raise ValueError(f"Pedido {pedido_id} não encontrado")
        return _to_dto(p)

    def marcar_enviado_cozinha(self, pedido_id: int) -> PedidoDTO:
        p = self._repo.atualizar_status(pedido_id, StatusPedido.ENVIADO_COZINHA)
        if not p:
            raise ValueError(f"Pedido {pedido_id} não encontrado")
        return _to_dto(p)

    # ── Métodos da API HTTP deste módulo ─────────────────────────────────────

    def criar_pedido(self, cliente: str, itens_in: list[dict]) -> PedidoDTO:
        itens_resolvidos = []
        for item_in in itens_in:
            # Consulta cardápio via INTERFACE pública — sem tocar em tabelas do cardápio
            item_cardapio = self._cardapio.obter_item(item_in["item_cardapio_id"])
            if not item_cardapio or not item_cardapio.disponivel:
                raise ValueError(f"Item {item_in['item_cardapio_id']} não disponível")
            itens_resolvidos.append({
                "item_cardapio_id": item_cardapio.id,
                "quantidade": item_in["quantidade"],
                "preco_unitario": item_cardapio.preco,
            })
        p = self._repo.criar(cliente=cliente, itens=itens_resolvidos)
        return _to_dto(p)

    def listar_pedidos(self) -> list[PedidoDTO]:
        return [_to_dto(p) for p in self._repo.listar()]

    def cancelar_pedido(self, pedido_id: int) -> PedidoDTO | None:
        p = self._repo.buscar_por_id(pedido_id)
        if not p:
            return None
        if p.status.value in ("PAGO", "ENVIADO_COZINHA"):
            raise ValueError("Pedido pago não pode ser cancelado")
        p = self._repo.cancelar(pedido_id)
        return _to_dto(p)
