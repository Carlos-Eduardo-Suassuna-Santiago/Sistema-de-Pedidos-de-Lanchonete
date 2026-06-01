# Versão 1 — Monólito

Sistema de Pedidos de Lanchonete implementado como monólito em **FastAPI + SQLite**.

---

## Estrutura

```
monolito/
├── main.py              # Ponto de entrada, registro dos routers
├── database.py          # Configuração do SQLAlchemy (único banco)
├── models.py            # Todos os modelos em um só lugar (acoplamento intencional)
├── requirements.txt
├── cardapio/
│   └── router.py        # CRUD de itens
├── pedidos/
│   └── router.py        # Criar, listar, cancelar
├── pagamento/
│   └── router.py        # Processar (mock) e consultar status
└── notificacao/
    └── router.py        # Consultar notificações enviadas à cozinha
```

> Os módulos existem como pastas, mas **sem fronteiras rígidas**: `pagamento/router.py`
> importa e escreve diretamente em `Notificacao` — acoplamento intencional conforme o enunciado.

---

## Como rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Subir a aplicação (porta 8000)
uvicorn main:app --reload

# 3. Acessar a documentação interativa
# http://localhost:8000/docs
```

### Com Docker

```bash
# Build da imagem
docker build -t monolito-lanchonete .

# Subir com Docker Compose
docker compose up --build
```

A aplicação fica disponível em `http://localhost:8000` e o SQLite é persistido em
`./data/lanchonete.db` via volume.

---

## Swagger rápido

Depois de subir a aplicação, abra:

`http://localhost:8000/docs`

No Swagger UI, os testes seguem esta ordem:

1. Crie um item no cardápio em `POST /cardapio/` com este JSON:

```json
{
  "nome": "X-Burguer",
  "descricao": "Hamburguer clássico",
  "preco": 18.5,
  "disponivel": true
}
```

2. Crie um pedido em `POST /pedidos/` usando o `item_cardapio_id` retornado no passo anterior:

```json
{
  "cliente": "João",
  "itens": [
    {
      "item_cardapio_id": 1,
      "quantidade": 2
    }
  ]
}
```

3. Processe o pagamento em `POST /pagamento/processar`:

```json
{
  "pedido_id": 1
}
```

4. Consulte a notificação da cozinha em `GET /notificacoes/1`.

5. Verifique o status do pagamento em `GET /pagamento/1/status`.

6. Confira a saúde da aplicação em `GET /health`.

---

## Passo a passo de testes

### Teste manual pelo Swagger

1. Inicie a aplicação com `uvicorn main:app --reload` ou com `docker compose up --build`.
2. Abra `http://localhost:8000/docs`.
3. Execute os endpoints na sequência: cardápio, pedidos, pagamento, notificações e health.
4. Se o Swagger retornar `200` ou `201`, o fluxo está funcionando.

### Teste rápido por terminal

1. Crie o item do cardápio.
2. Crie o pedido com o ID do item.
3. Processe o pagamento com o ID do pedido.
4. Consulte a notificação do pedido.
5. Consulte o health check.

Exemplo completo com `curl`:

```bash
curl -X POST http://localhost:8000/cardapio/ \
  -H "Content-Type: application/json" \
  -d '{"nome":"X-Burguer","descricao":"Hamburguer clássico","preco":18.5,"disponivel":true}'

curl -X POST http://localhost:8000/pedidos/ \
  -H "Content-Type: application/json" \
  -d '{"cliente":"João","itens":[{"item_cardapio_id":1,"quantidade":2}]}'

curl -X POST http://localhost:8000/pagamento/processar \
  -H "Content-Type: application/json" \
  -d '{"pedido_id":1}'

curl http://localhost:8000/notificacoes/1

curl http://localhost:8000/health
```

---

## Fluxo completo

```
POST /cardapio/          → cria itens no cardápio
POST /pedidos/           → cria pedido com os itens
POST /pagamento/processar → paga o pedido (mock)
                           └─ internamente: cria Notificacao + muda status para ENVIADO_COZINHA
GET  /notificacoes/      → cozinha vê os pedidos prontos para preparo
GET  /health             → health check
```

### Exemplo rápido (curl)

```bash
# 1. Criar item no cardápio
curl -X POST http://localhost:8000/cardapio/ \
  -H "Content-Type: application/json" \
  -d '{"nome": "X-Burguer", "preco": 18.50}'

# 2. Criar pedido
curl -X POST http://localhost:8000/pedidos/ \
  -H "Content-Type: application/json" \
  -d '{"cliente": "João", "itens": [{"item_cardapio_id": 1, "quantidade": 2}]}'

# 3. Processar pagamento
curl -X POST http://localhost:8000/pagamento/processar \
  -H "Content-Type: application/json" \
  -d '{"pedido_id": 1}'

# 4. Verificar notificação da cozinha
curl http://localhost:8000/notificacoes/1

# 5. Health check
curl http://localhost:8000/health
```

---

## ✅ Checklist

- [x] Única aplicação rodando em uma porta (8000)
- [x] Banco único (`lanchonete.db`) com todas as tabelas
- [x] Fluxo completo funcional: criar pedido → pagar → notificar cozinha
- [x] Endpoint de health check (`GET /health`)
- [x] Experimento obrigatório documentado abaixo
- [x] Documentação sobre escala do cardápio

---

## 🧪 Experimento Obrigatório — Lentidão no Pagamento

### Como ativar

```bash
# Subir com lentidão simulada (sleep 5s no /pagamento/processar)
SIMULAR_LENTIDAO=true uvicorn main:app --reload --workers 1
```

### O que acontece

Com `--workers 1`, o uvicorn usa **um único processo**. O `time.sleep(5)` dentro de
`/pagamento/processar` **bloqueia o event loop inteiro** por 5 segundos.

Durante esse tempo, qualquer outra requisição (ex: `GET /cardapio/`) fica na fila
esperando — mesmo sendo completamente independente de pagamento.

**Teste prático:**

```bash
# Terminal 1 — dispara pagamento (vai travar 5s)
curl -X POST http://localhost:8000/pagamento/processar \
  -d '{"pedido_id": 1}' -H "Content-Type: application/json" &

# Terminal 2 — tenta listar o cardápio ao mesmo tempo
time curl http://localhost:8000/cardapio/
# Resultado: demora ~5s para responder, mesmo sem relação com pagamento
```

### Conclusão do experimento

| Cenário | Comportamento |
|---|---|
| `--workers 1` + lentidão | Todos os endpoints ficam lentos — ponto único de falha |
| `--workers 4` + lentidão | Outros workers respondem normalmente enquanto 1 está ocupado |
| Microsserviços | Lentidão em pagamento **não afeta** cardápio ou pedidos |

> **Lição:** No monólito, uma falha ou lentidão em qualquer módulo pode degradar toda a aplicação.

---

## 📋 Se o cardápio precisasse escalar 10x

O módulo de cardápio é o mais lido (clientes consultam frequentemente, raramente escrevem).
Para escalar 10x mais que o resto, no monólito seria necessário:

1. **Escalar a aplicação inteira** — não existe forma de escalar só o cardápio.
   Isso significa mais instâncias de tudo: pedidos, pagamento e notificação também.

2. **Banco de dados vira gargalo** — o SQLite não suporta múltiplas instâncias.
   Migrar para PostgreSQL seria obrigatório, com connection pooling (ex: PgBouncer).

3. **Adicionar cache** (Redis) na frente do cardápio para reduzir leituras ao banco.

4. **Custo desnecessário** — pagar por recursos de pagamento/pedidos só porque o
   cardápio precisa de mais capacidade.

> **Conclusão:** Escalar seletivamente é inviável no monólito. A solução correta seria
> extrair o cardápio como microsserviço — o que leva naturalmente à Versão 3.
