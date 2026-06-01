from sqlalchemy.orm import Session
from notificacao.interfaces.notificacao_interface import NotificacaoServiceInterface, NotificacaoDTO
from notificacao.repository.notificacao_repository import NotificacaoRepository


def _to_dto(n) -> NotificacaoDTO:
    return NotificacaoDTO(id=n.id, pedido_id=n.pedido_id, mensagem=n.mensagem, enviada_em=n.enviada_em)


class NotificacaoService(NotificacaoServiceInterface):
    def __init__(self, db: Session):
        self._repo = NotificacaoRepository(db)

    def notificar_cozinha(self, pedido_id: int, cliente: str) -> NotificacaoDTO:
        mensagem = f"Pedido #{pedido_id} do cliente '{cliente}' foi pago — iniciar preparo."
        n = self._repo.criar(pedido_id=pedido_id, mensagem=mensagem)
        return _to_dto(n)

    def listar(self) -> list[NotificacaoDTO]:
        return [_to_dto(n) for n in self._repo.listar()]

    def buscar_por_pedido(self, pedido_id: int) -> NotificacaoDTO | None:
        n = self._repo.buscar_por_pedido(pedido_id)
        return _to_dto(n) if n else None
