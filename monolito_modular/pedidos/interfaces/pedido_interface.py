"""
Interface pública do módulo Pedidos.
Expõe apenas DTOs e o contrato de serviço — sem ORM, sem SQLAlchemy, sem entidades internas.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StatusPedidoDTO(str, Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"
    ENVIADO_COZINHA = "ENVIADO_COZINHA"


@dataclass
class ItemPedidoDTO:
    id: int
    item_cardapio_id: int
    quantidade: int
    preco_unitario: float


@dataclass
class PedidoDTO:
    id: int
    cliente: str
    status: StatusPedidoDTO
    criado_em: datetime
    itens: list[ItemPedidoDTO] = field(default_factory=list)

    @property
    def valor_total(self) -> float:
        return sum(i.preco_unitario * i.quantidade for i in self.itens)


class PedidoServiceInterface(ABC):
    @abstractmethod
    def obter_pedido(self, pedido_id: int) -> PedidoDTO | None:
        ...

    @abstractmethod
    def marcar_como_pago(self, pedido_id: int) -> PedidoDTO:
        """Chamado pelo módulo de Pagamento via interface — nunca diretamente no ORM."""
        ...

    @abstractmethod
    def marcar_enviado_cozinha(self, pedido_id: int) -> PedidoDTO:
        ...
