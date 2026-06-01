from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from database import get_db
from models import Pagamento, Pedido, Notificacao, StatusPedido, StatusPagamento
import time
import os

router = APIRouter()

# Variável de controle para o experimento de lentidão (Checklist item obrigatório)
# Para ativar: defina a variável de ambiente SIMULAR_LENTIDAO=true
SIMULAR_LENTIDAO = os.getenv("SIMULAR_LENTIDAO", "false").lower() == "true"


class PagamentoCreate(BaseModel):
    pedido_id: int


class PagamentoOut(BaseModel):
    id: int
    pedido_id: int
    status: StatusPagamento
    valor: float
    processado_em: datetime | None

    class Config:
        from_attributes = True


@router.post("/processar", response_model=PagamentoOut, status_code=201)
def processar_pagamento(dados: PagamentoCreate, db: Session = Depends(get_db)):
    """
    Processa o pagamento de um pedido (mock).
    
    EXPERIMENTO OBRIGATÓRIO:
    - Com SIMULAR_LENTIDAO=false (padrão): resposta imediata.
    - Com SIMULAR_LENTIDAO=true: sleep de 5s — todos os outros endpoints
      ficam bloqueados enquanto o servidor processa este request,
      pois o monólito compartilha o mesmo processo/thread pool.
    """
    if SIMULAR_LENTIDAO:
        # Simula lentidão: bloqueia o thread inteiro por 5 segundos.
        # Observação: com uvicorn --workers 1, outros endpoints ficam lentos.
        # Suba com --workers 4 para ver diferença de concorrência.
        time.sleep(5)

    pedido = db.query(Pedido).filter(Pedido.id == dados.pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if pedido.status == StatusPedido.CANCELADO:
        raise HTTPException(status_code=400, detail="Pedido cancelado não pode ser pago")
    if pedido.status in (StatusPedido.PAGO, StatusPedido.ENVIADO_COZINHA):
        raise HTTPException(status_code=400, detail="Pedido já foi pago")

    # Verifica se já existe pagamento
    pagamento_existente = db.query(Pagamento).filter(
        Pagamento.pedido_id == dados.pedido_id
    ).first()
    if pagamento_existente:
        raise HTTPException(status_code=409, detail="Pagamento já registrado para este pedido")

    # Calcula valor total
    valor_total = sum(
        item.preco_unitario * item.quantidade for item in pedido.itens
    )

    # Mock: pagamento sempre aprovado
    pagamento = Pagamento(
        pedido_id=dados.pedido_id,
        status=StatusPagamento.APROVADO,
        valor=valor_total,
        processado_em=datetime.utcnow(),
    )
    db.add(pagamento)

    # Atualiza status do pedido
    pedido.status = StatusPedido.PAGO

    # ─── REGRA DE NEGÓCIO CRÍTICA ────────────────────────────────────────────
    # Só notifica a cozinha APÓS confirmação de pagamento.
    # No monólito isso é uma chamada direta de função — sem fronteiras.
    notificacao = Notificacao(
        pedido_id=pedido.id,
        mensagem=f"Pedido #{pedido.id} do cliente '{pedido.cliente}' foi pago e está pronto para preparo.",
    )
    db.add(notificacao)
    pedido.status = StatusPedido.ENVIADO_COZINHA
    # ─────────────────────────────────────────────────────────────────────────

    db.commit()
    db.refresh(pagamento)
    return pagamento


@router.get("/{pedido_id}/status", response_model=PagamentoOut)
def consultar_status(pedido_id: int, db: Session = Depends(get_db)):
    pagamento = db.query(Pagamento).filter(Pagamento.pedido_id == pedido_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado para este pedido")
    return pagamento
