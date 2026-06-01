"""
Interface pública do módulo Cardápio.
Nenhum outro módulo pode acessar repositórios ou modelos internos deste módulo —
apenas os tipos e métodos definidos aqui.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ItemCardapioDTO:
    """Tipo de saída público. Outros módulos usam este DTO, nunca o ORM interno."""
    id: int
    nome: str
    descricao: str
    preco: float
    disponivel: bool


class CardapioServiceInterface(ABC):
    @abstractmethod
    def obter_item(self, item_id: int) -> ItemCardapioDTO | None:
        """Retorna um item do cardápio ou None se não existir/indisponível."""
        ...
