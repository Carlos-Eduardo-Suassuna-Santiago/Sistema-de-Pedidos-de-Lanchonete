"""
PagamentoService orquestra a regra de negócio crítica:
  pedido pago → notificar cozinha

Comunica-se com Pedidos e Notificação APENAS via suas interfaces públicas.
Não importa nenhum repositório ou modelo ORM de outro módulo.
"""
from sqlalchemy.orm import Session
from pagamento.interfaces.pagamento_interface import PagamentoServiceInterface, PagamentoDTO, StatusPagamentoDTO
from pagamento.repository.pagamento_repository import PagamentoRepository
from pedidos.interfaces.pedido_interface import PedidoServiceInterface, StatusPedidoDTO
from notificacao.interfaces.notificacao_interface import NotificacaoServiceInterface


def _to_dto(p) -> PagamentoDTO:
    return PagamentoDTO(
        id=p.id,
        pedido_id=p.pedido_id,
        status=StatusPagamentoDTO(p.status.value),
        valor=p.valor,
        processado_em=p.processado_em,
    )


class PagamentoService(PagamentoServiceInterface):
    def __init__(
        self,
        db: Session,
        pedido_svc: PedidoServiceInterface,
        notificacao_svc: NotificacaoServiceInterface,
    ):
        self._repo = PagamentoRepository(db)
        # Dependências injetadas via interface — nunca imports diretos de outros módulos
        self._pedidos = pedido_svc
        self._notificacoes = notificacao_svc

    def processar(self, pedido_id: int) -> PagamentoDTO:
        # 1. Consulta pedido via interface pública de Pedidos
        pedido = self._pedidos.obter_pedido(pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado")
        if pedido.status == StatusPedidoDTO.CANCELADO:
            raise ValueError("Pedido cancelado não pode ser pago")
        if pedido.status in (StatusPedidoDTO.PAGO, StatusPedidoDTO.ENVIADO_COZINHA):
            raise ValueError("Pedido já foi pago")
        if self._repo.buscar_por_pedido(pedido_id):
            raise ValueError("Pagamento já registrado para este pedido")

        # 2. Registra pagamento no próprio repositório (nunca escreve em tabela alheia)
        pagamento = self._repo.criar(pedido_id=pedido_id, valor=pedido.valor_total)

        # 3. ── REGRA CRÍTICA ─────────────────────────────────────────────────
        #    Atualiza status do pedido via interface de Pedidos
        self._pedidos.marcar_como_pago(pedido_id)

        #    Notifica cozinha via interface de Notificação
        self._notificacoes.notificar_cozinha(pedido_id=pedido_id, cliente=pedido.cliente)

        #    Marca pedido como enviado à cozinha via interface de Pedidos
        self._pedidos.marcar_enviado_cozinha(pedido_id)
        # ─────────────────────────────────────────────────────────────────────

        return _to_dto(pagamento)

    def consultar_status(self, pedido_id: int) -> PagamentoDTO | None:
        p = self._repo.buscar_por_pedido(pedido_id)
        return _to_dto(p) if p else None
