"""
Serviço de Notificação
- Consome mensagens da fila 'pedido.pago' via RabbitMQ (assíncrono)
- Persiste notificações no banco próprio
- Expõe API HTTP para consulta

EXPERIMENTO: Derrube este serviço (docker stop lanchonete-notificacao).
O pagamento continua funcionando — a mensagem fica na fila do RabbitMQ.
Quando o serviço volta, ele processa tudo que ficou acumulado.
O pagamento NUNCA falha por causa da notificação.
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from pydantic import BaseModel
from datetime import datetime
from contextlib import asynccontextmanager
import aio_pika
import asyncio
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notificacao")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notificacao.db")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://lanchonete:lanchonete123@localhost:5672/")
QUEUE_NAME = "pedido.pago"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Notificacao(Base):
    __tablename__ = "notificacoes"
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, nullable=False, index=True)
    cliente = Column(String, nullable=False)
    mensagem = Column(String, nullable=False)
    recebida_em = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def salvar_notificacao(pedido_id: int, cliente: str):
    """Salva notificação no banco — chamado pela callback do consumer."""
    db = SessionLocal()
    try:
        mensagem = f"Pedido #{pedido_id} do cliente '{cliente}' pago — iniciar preparo!"
        n = Notificacao(pedido_id=pedido_id, cliente=cliente, mensagem=mensagem)
        db.add(n)
        db.commit()
        logger.info(f"[COZINHA] {mensagem}")
    finally:
        db.close()


async def consumir_fila():
    """
    Consumer assíncrono da fila RabbitMQ.
    Roda em background durante toda a vida do serviço.
    Mensagens ficam na fila até processamento com sucesso (durable=True).
    """
    for tentativa in range(10):
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            break
        except Exception as e:
            logger.warning(f"Aguardando RabbitMQ... tentativa {tentativa + 1}/10 ({e})")
            await asyncio.sleep(3)
    else:
        logger.error("Não foi possível conectar ao RabbitMQ após 10 tentativas")
        return

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        logger.info(f"Consumer conectado. Aguardando mensagens em '{QUEUE_NAME}'...")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = json.loads(message.body.decode())
                        salvar_notificacao(payload["pedido_id"], payload["cliente"])
                    except Exception as e:
                        logger.error(f"Erro ao processar mensagem: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(consumir_fila())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Serviço Notificação", version="1.0.0", lifespan=lifespan)


class NotificacaoOut(BaseModel):
    id: int
    pedido_id: int
    cliente: str
    mensagem: str
    recebida_em: datetime

    class Config:
        from_attributes = True


@app.get("/health")
def health():
    return {"status": "ok", "service": "notificacao"}


@app.get("/notificacoes/", response_model=list[NotificacaoOut])
def listar(db: Session = Depends(get_db)):
    return db.query(Notificacao).order_by(Notificacao.recebida_em.desc()).all()


@app.get("/notificacoes/{pedido_id}", response_model=NotificacaoOut)
def buscar(pedido_id: int, db: Session = Depends(get_db)):
    n = db.query(Notificacao).filter(Notificacao.pedido_id == pedido_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    return n
