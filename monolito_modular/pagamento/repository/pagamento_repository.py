from sqlalchemy.orm import Session
from pagamento.repository.models import Pagamento, StatusPagamento
from datetime import datetime


class PagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, pedido_id: int, valor: float) -> Pagamento:
        p = Pagamento(
            pedido_id=pedido_id,
            status=StatusPagamento.APROVADO,
            valor=valor,
            processado_em=datetime.utcnow(),
        )
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def buscar_por_pedido(self, pedido_id: int) -> Pagamento | None:
        return self.db.query(Pagamento).filter(Pagamento.pedido_id == pedido_id).first()
