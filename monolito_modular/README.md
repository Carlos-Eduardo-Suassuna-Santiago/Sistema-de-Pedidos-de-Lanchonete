# Versão 2 — Monólito Modular

Sistema de Pedidos de Lanchonete com **fronteiras explícitas entre módulos**, implementado em FastAPI + SQLite.

---

## Estrutura

```
monolito_modular/
├── main.py
├── database.py
├── requirements.txt
├── cardapio/
│   ├── interfaces/
│   │   └── cardapio_interface.py   ← CONTRATO PÚBLICO (CardapioServiceInterface, ItemCardapioDTO)
│   ├── repository/
│   │   ├── models.py               ← ORM privado (tabela: cardapio__itens)
│   │   └── cardapio_repository.py  ← privado
│   ├── service/
│   │   └── cardapio_service.py     ← implementa a interface pública
│   └── router.py
├── pedidos/
│   ├── interfaces/
│   │   └── pedido_interface.py     ← CONTRATO PÚBLICO
│   ├── repository/  ...
│   ├── service/
│   │   └── pedido_service.py       ← injeta CardapioServiceInterface
│   └── router.py
├── pagamento/
│   ├── interfaces/
│   │   └── pagamento_interface.py  ← CONTRATO PÚBLICO
│   ├── repository/  ...
│   ├── service/
│   │   └── pagamento_service.py    ← injeta PedidoServiceInterface + NotificacaoServiceInterface
│   └── router.py
└── notificacao/
    ├── interfaces/
    │   └── notificacao_interface.py ← CONTRATO PÚBLICO
    ├── repository/  ...
    ├── service/
    │   └── notificacao_service.py
    └── router.py
```

### Regras de fronteira (enforcement manual)

| De → Para | Permitido? | Como |
|---|---|---|
| `pagamento` → `pedidos.repository` | ❌ | Proibido — usa `PedidoServiceInterface` |
| `pagamento` → `pedidos.service` | ✅ | Via interface injetada no construtor |
| `pedidos` → `cardapio.repository` | ❌ | Proibido — usa `CardapioServiceInterface.obter_item()` |
| Qualquer módulo → tabela alheia | ❌ | Schemas separados por prefixo |

---

## Como rodar

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# http://localhost:8000/docs
```

### Rodando com Docker (desenvolvimento)

1. Buildar a imagem e subir o container:

```bash
docker-compose up --build
```

2. Acesse a API em `http://localhost:8000/docs`.

Observações:
- O `docker-compose.yml` monta o diretório atual na imagem para habilitar hot-reload durante o desenvolvimento.
- O banco SQLite `lanchonete_modular.db` será criado no diretório do projeto no host, preservando dados entre reinícios do container.

### Rodando com Docker (imagem única)

```bash
docker build -t monolito-modular:latest .
docker run -p 8000:8000 monolito-modular:latest
```


---

## Fluxo completo

```
POST /cardapio/           → cria item
POST /pedidos/            → cria pedido (consulta cardápio via interface)
POST /pagamento/processar → paga → atualiza pedido via interface → notifica cozinha via interface
GET  /notificacoes/       → cozinha consulta pedidos prontos
GET  /health
```

### Exemplo rápido (curl)

```bash
# 1. Item no cardápio
curl -X POST http://localhost:8000/cardapio/ \
  -H "Content-Type: application/json" \
  -d '{"nome": "X-Tudo", "preco": 22.00}'

# 2. Pedido
curl -X POST http://localhost:8000/pedidos/ \
  -H "Content-Type: application/json" \
  -d '{"cliente": "Ana", "itens": [{"item_cardapio_id": 1, "quantidade": 1}]}'

# 3. Pagamento
curl -X POST http://localhost:8000/pagamento/processar \
  -H "Content-Type: application/json" \
  -d '{"pedido_id": 1}'

# 4. Notificação
curl http://localhost:8000/notificacoes/1
```

---

## ✅ Checklist

- [x] Cada módulo tem sua própria camada de interface (`CardapioServiceInterface`, `PedidoServiceInterface`, etc.)
- [x] Nenhum módulo acessa tabela/repositório de outro diretamente
- [x] Schemas separados no banco por prefixo (`cardapio__*`, `pedidos__*`, `pagamento__*`, `notificacao__*`)
- [x] Comunicação entre módulos via interfaces tipadas (sem acoplamento por ORM/entidade alheia)
- [x] Experimento obrigatório documentado abaixo
- [x] Documentação sobre quais módulos virariam serviços

---

## 🧪 Experimento Obrigatório — Trocar implementação do Pagamento

**Cenário:** trocar o mock de pagamento (sempre aprova) por uma implementação que recusa pedidos acima de R$ 100,00.

### O que foi necessário mudar

**Apenas 1 arquivo:** `pagamento/repository/pagamento_repository.py`

```python
# Antes: sempre APROVADO
p = Pagamento(status=StatusPagamento.APROVADO, ...)

# Depois: lógica condicional
status = StatusPagamento.APROVADO if valor <= 100 else StatusPagamento.RECUSADO
p = Pagamento(status=status, ...)
```

**Nenhum outro módulo foi alterado** — Pedidos, Cardápio e Notificação não sabem nada sobre a lógica interna de pagamento.

### Esforço medido

| Etapa | Tempo estimado |
|---|---|
| Localizar o arquivo correto | ~10 segundos (estrutura clara) |
| Implementar a mudança | ~2 minutos |
| Testar que outros módulos não quebraram | ~1 minuto (rodar /docs) |
| **Total** | **~3 minutos** |

Comparado ao monólito, onde a lógica de pagamento estava misturada ao router e ao registro de notificação no mesmo bloco, exigiria mais cuidado para não quebrar o fluxo.

---

## 📋 Quais módulos poderiam virar serviços independentes?

### Cardápio — candidato imediato ✅

- Sem dependências de outros módulos (ninguém escreve nele)
- Interface pública já existe: `CardapioServiceInterface`
- O que falta: trocar a injeção local por uma chamada HTTP/gRPC

### Notificação — candidato imediato ✅

- Só recebe chamadas, não chama ninguém
- Interface já existe: `NotificacaoServiceInterface`
- O que falta: substituir a implementação por um producer de fila (Kafka/RabbitMQ)

### Pedidos — candidato médio ⚠️

- Depende de Cardápio (para validar itens ao criar pedido)
- Extração exige ou uma chamada HTTP a Cardápio, ou replicar dados de preço no evento de criação
- O que falta: decidir a estratégia de consistência eventual

### Pagamento — candidato médio ⚠️

- Orquestra Pedidos + Notificação — relação acoplada pela regra de negócio crítica
- Extração exigiria transações distribuídas ou saga pattern
- O que falta: implementar compensação de falha (ex: pedido marcado como pago, mas notificação falhou)

---

## Testes rápidos via Swagger UI

Siga estes passos rápidos usando a interface Swagger fornecida pelo FastAPI em `/docs`.

1. Suba a aplicação (docker-compose recomenda-se para desenvolvimento):

```bash
docker-compose up --build
```

2. Abra o Swagger UI em `http://localhost:8000/docs`.

3. Teste os endpoints na sequência (use "Try it out" → preencha o JSON → "Execute"):

- **POST /cardapio/** — criar item
  - Body de exemplo:

```json
{ "nome": "X-Tudo", "preco": 22.00 }
```

- **POST /pedidos/** — criar pedido (use `item_cardapio_id` retornado no passo anterior)
  - Body de exemplo:

```json
{ "cliente": "Ana", "itens": [{ "item_cardapio_id": 1, "quantidade": 1 }] }
```

- **POST /pagamento/processar** — processar pagamento (use `pedido_id` do passo anterior)
  - Body de exemplo:

```json
{ "pedido_id": 1 }
```

- **GET /notificacoes/{pedido_id}** — consultar notificações/pedidos prontos (substitua `{pedido_id}`)

- **GET /health** — verificar status da aplicação

4. (Opcional) Se preferir, repita os mesmos testes via `curl` a partir do host:

```bash
curl -X POST http://localhost:8000/cardapio/ -H "Content-Type: application/json" -d '{"nome":"X-Tudo","preco":22.00}'
curl -X POST http://localhost:8000/pedidos/ -H "Content-Type: application/json" -d '{"cliente":"Ana","itens":[{"item_cardapio_id":1,"quantidade":1}]}'
curl -X POST http://localhost:8000/pagamento/processar -H "Content-Type: application/json" -d '{"pedido_id":1}'
curl http://localhost:8000/notificacoes/1
curl http://localhost:8000/health
```

Dica: o Swagger UI mostra o corpo de resposta e o `response` com os IDs gerados — copie-os para os passos seguintes.

