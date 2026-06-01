from sqlalchemy.orm import Session
from notificacao.repository.models import Notificacao


class NotificacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, pedido_id: int, mensagem: str) -> Notificacao:
        n = Notificacao(pedido_id=pedido_id, mensagem=mensagem)
        self.db.add(n)
        self.db.commit()
        self.db.refresh(n)
        return n

    def listar(self) -> list[Notificacao]:
        return self.db.query(Notificacao).order_by(Notificacao.enviada_em.desc()).all()

    def buscar_por_pedido(self, pedido_id: int) -> Notificacao | None:
        return self.db.query(Notificacao).filter(Notificacao.pedido_id == pedido_id).first()
