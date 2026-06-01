"""
Interface pública do módulo Notificação.
O módulo de Pagamento chama apenas este contrato — nunca acessa
repositórios ou modelos internos de Notificação diretamente.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NotificacaoDTO:
    id: int
    pedido_id: int
    mensagem: str
    enviada_em: datetime


class NotificacaoServiceInterface(ABC):
    @abstractmethod
    def notificar_cozinha(self, pedido_id: int, cliente: str) -> NotificacaoDTO:
        """Envia notificação à cozinha sobre pedido pago."""
        ...

    @abstractmethod
    def listar(self) -> list[NotificacaoDTO]:
        ...

    @abstractmethod
    def buscar_por_pedido(self, pedido_id: int) -> NotificacaoDTO | None:
        ...
