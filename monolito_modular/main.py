from fastapi import FastAPI
from database import Base, engine

# Importar todos os models para que o SQLAlchemy os registre antes do create_all
import cardapio.repository.models  # noqa
import pedidos.repository.models   # noqa
import pagamento.repository.models  # noqa
import notificacao.repository.models  # noqa

import cardapio.router as cardapio_router
import pedidos.router as pedidos_router
import pagamento.router as pagamento_router
import notificacao.router as notificacao_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lanchonete — Monólito Modular", version="2.0.0")

app.include_router(cardapio_router.router, prefix="/cardapio", tags=["Cardápio"])
app.include_router(pedidos_router.router, prefix="/pedidos", tags=["Pedidos"])
app.include_router(pagamento_router.router, prefix="/pagamento", tags=["Pagamento"])
app.include_router(notificacao_router.router, prefix="/notificacoes", tags=["Notificação"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "monolito-modular"}
