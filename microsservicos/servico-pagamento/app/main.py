"""
Serviço de Pagamento — orquestra a regra de negócio crítica:
  1. Consulta pedido via HTTP síncrono → Serviço Pedidos
  2. Registra pagamento no banco próprio
  3. Atualiza status do pedido via HTTP síncrono → Serviço Pedidos
  4. Publica evento 'pedido.pago' na fila RabbitMQ (assíncrono)
     └→ Serviço de Notificação consome em background

O pagamento retorna SUCESSO mesmo que o Serviço de Notificação esteja offline.
A mensagem fica na fila até o serviço de notificação voltar (at-least-once delivery).
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, Float, DateTime, Enum
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from pydantic import BaseModel
from datetime import datetime
from contextlib import asynccontextmanager
import aio_pika
import asyncio
import httpx
import enum
import json
import os
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pagamento")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pagamento.db")
PEDIDOS_URL  = os.getenv("PEDIDOS_URL", "http://localhost:8002")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://lanchonete:lanchonete123@localhost:5672/")
QUEUE_NAME   = "pedido.pago"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

# Conexão global reutilizável com RabbitMQ
_rabbitmq_connection = None
_rabbitmq_channel    = None


class Base(DeclarativeBase):
    pass


class StatusPagamento(str, enum.Enum):
    PENDENTE  = "PENDENTE"
    APROVADO  = "APROVADO"
    RECUSADO  = "RECUSADO"


class Pagamento(Base):
    __tablename__ = "pagamentos"
    id            = Column(Integer, primary_key=True, index=True)
    pedido_id     = Column(Integer, nullable=False, unique=True, index=True)
    status        = Column(Enum(StatusPagamento), default=StatusPagamento.APROVADO)
    valor         = Column(Float, nullable=False)
    processado_em = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)


async def conectar_rabbitmq():
    global _rabbitmq_connection, _rabbitmq_channel
    for tentativa in range(10):
        try:
            _rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            _rabbitmq_channel    = await _rabbitmq_connection.channel()
            # Garante que a fila existe antes de publicar
            await _rabbitmq_channel.declare_queue(QUEUE_NAME, durable=True)
            logger.info("Conectado ao RabbitMQ")
            return
        except Exception as e:
            logger.warning(f"Aguardando RabbitMQ... {tentativa + 1}/10 ({e})")
            await asyncio.sleep(3)
    logger.error("Não foi possível conectar ao RabbitMQ")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await conectar_rabbitmq()
    yield
    if _rabbitmq_connection:
        await _rabbitmq_connection.close()


app = FastAPI(title="Serviço Pagamento", version="1.0.0", lifespan=lifespan)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Resiliência: retry ao chamar Pedidos ─────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(httpx.RequestError),
)
def _http_get_pedido(pedido_id: int) -> dict:
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{PEDIDOS_URL}/pedidos/{pedido_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(httpx.RequestError),
)
def _http_patch_status(pedido_id: int, status: str):
    with httpx.Client(timeout=5.0) as client:
        resp = client.patch(
            f"{PEDIDOS_URL}/pedidos/{pedido_id}/status",
            json={"status": status},
        )
        resp.raise_for_status()


async def publicar_evento(pedido_id: int, cliente: str, valor: float):
    """
    Publica evento assíncrono na fila. Fire-and-forget:
    se o serviço de notificação estiver offline, a mensagem fica na fila (durable).
    O pagamento já foi registrado — não reverte por falha de notificação.
    """
    if not _rabbitmq_channel:
        logger.error("Canal RabbitMQ indisponível — evento não publicado")
        return
    payload = json.dumps({"pedido_id": pedido_id, "cliente": cliente, "valor": valor})
    await _rabbitmq_channel.default_exchange.publish(
        aio_pika.Message(
            body=payload.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # sobrevive a restart do broker
        ),
        routing_key=QUEUE_NAME,
    )
    logger.info(f"Evento publicado na fila '{QUEUE_NAME}' — pedido #{pedido_id}")


# ── Schemas ──────────────────────────────────────────────────────────────────
class PagamentoIn(BaseModel):
    pedido_id: int


class PagamentoOut(BaseModel):
    id: int
    pedido_id: int
    status: StatusPagamento
    valor: float
    processado_em: datetime | None

    class Config:
        from_attributes = True


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "pagamento"}


@app.post("/pagamento/processar", response_model=PagamentoOut, status_code=201)
async def processar(dados: PagamentoIn, db: Session = Depends(get_db)):
    # 1. Consulta pedido via HTTP síncrono
    try:
        pedido = _http_get_pedido(dados.pedido_id)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Serviço de pedidos indisponível")

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if pedido["status"] in ("CANCELADO",):
        raise HTTPException(status_code=400, detail="Pedido cancelado não pode ser pago")
    if pedido["status"] in ("PAGO", "ENVIADO_COZINHA"):
        raise HTTPException(status_code=400, detail="Pedido já foi pago")

    # Idempotência: não duplica pagamento
    if db.query(Pagamento).filter(Pagamento.pedido_id == dados.pedido_id).first():
        raise HTTPException(status_code=409, detail="Pagamento já registrado")

    # 2. Registra pagamento (mock: sempre aprovado)
    valor = pedido.get("valor_total") or sum(
        i["preco_unitario"] * i["quantidade"] for i in pedido["itens"]
    )
    pagamento = Pagamento(
        pedido_id=dados.pedido_id,
        status=StatusPagamento.APROVADO,
        valor=valor,
        processado_em=datetime.utcnow(),
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    # 3. Atualiza status do pedido via HTTP síncrono
    try:
        _http_patch_status(dados.pedido_id, "ENVIADO_COZINHA")
    except httpx.RequestError:
        logger.warning(f"Falha ao atualizar status do pedido #{dados.pedido_id} — seguindo mesmo assim")

    # 4. ── REGRA CRÍTICA ───────────────────────────────────────────────────
    #    Publica evento assíncrono → Notificação consome da fila
    #    Fire-and-forget: pagamento já confirmado, notificação é eventual
    await publicar_evento(dados.pedido_id, pedido["cliente"], valor)
    # ─────────────────────────────────────────────────────────────────────

    return pagamento


@app.get("/pagamento/{pedido_id}/status", response_model=PagamentoOut)
def consultar_status(pedido_id: int, db: Session = Depends(get_db)):
    p = db.query(Pagamento).filter(Pagamento.pedido_id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return p
