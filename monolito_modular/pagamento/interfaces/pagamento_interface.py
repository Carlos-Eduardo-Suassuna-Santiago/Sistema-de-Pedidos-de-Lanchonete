"""
Interface pública do módulo Pagamento.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class StatusPagamentoDTO(str, Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


@dataclass
class PagamentoDTO:
    id: int
    pedido_id: int
    status: StatusPagamentoDTO
    valor: float
    processado_em: datetime | None


class PagamentoServiceInterface(ABC):
    @abstractmethod
    def processar(self, pedido_id: int) -> PagamentoDTO:
        ...

    @abstractmethod
    def consultar_status(self, pedido_id: int) -> PagamentoDTO | None:
        ...
