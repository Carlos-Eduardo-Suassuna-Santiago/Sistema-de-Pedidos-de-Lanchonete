from sqlalchemy.orm import Session
from cardapio.interfaces.cardapio_interface import CardapioServiceInterface, ItemCardapioDTO
from cardapio.repository.cardapio_repository import CardapioRepository


def _to_dto(item) -> ItemCardapioDTO:
    return ItemCardapioDTO(
        id=item.id,
        nome=item.nome,
        descricao=item.descricao or "",
        preco=item.preco,
        disponivel=item.disponivel,
    )


class CardapioService(CardapioServiceInterface):
    """
    Implementação concreta do serviço de cardápio.
    Esta é a ÚNICA classe que outros módulos podem instanciar/injetar.
    Internamente usa CardapioRepository — detalhe privado deste módulo.
    """

    def __init__(self, db: Session):
        self._repo = CardapioRepository(db)

    # ── Interface pública (contrato com outros módulos) ──────────────────────

    def obter_item(self, item_id: int) -> ItemCardapioDTO | None:
        item = self._repo.buscar_por_id(item_id)
        if not item:
            return None
        return _to_dto(item)

    # ── Métodos exclusivos da API HTTP deste módulo ──────────────────────────

    def criar_item(self, nome: str, descricao: str, preco: float, disponivel: bool) -> ItemCardapioDTO:
        item = self._repo.criar(nome=nome, descricao=descricao, preco=preco, disponivel=disponivel)
        return _to_dto(item)

    def listar_itens(self) -> list[ItemCardapioDTO]:
        return [_to_dto(i) for i in self._repo.listar()]

    def atualizar_item(self, item_id: int, dados: dict) -> ItemCardapioDTO | None:
        item = self._repo.atualizar(item_id, dados)
        return _to_dto(item) if item else None

    def deletar_item(self, item_id: int) -> bool:
        return self._repo.deletar(item_id)
