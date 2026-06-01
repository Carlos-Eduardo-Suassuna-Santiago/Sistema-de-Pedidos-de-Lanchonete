from fastapi import FastAPI
from database import engine, Base
import pedidos.router as pedidos_router
import cardapio.router as cardapio_router
import pagamento.router as pagamento_router
import notificacao.router as notificacao_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lanchonete - Monólito", version="1.0.0")

app.include_router(pedidos_router.router, prefix="/pedidos", tags=["Pedidos"])
app.include_router(cardapio_router.router, prefix="/cardapio", tags=["Cardápio"])
app.include_router(pagamento_router.router, prefix="/pagamento", tags=["Pagamento"])
app.include_router(notificacao_router.router, prefix="/notificacoes", tags=["Notificação"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "monolito"}
