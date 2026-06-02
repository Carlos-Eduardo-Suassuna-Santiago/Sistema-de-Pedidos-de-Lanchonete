# Versão 3 — Microsserviços

Sistema de Pedidos de Lanchonete com **4 serviços independentes**, orquestrados por Docker Compose.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│  Cliente (curl / /docs)                                         │
└──────┬──────────────────────────────────────────────────────────┘
       │ HTTP
┌──────▼──────┐   HTTP    ┌──────────────┐   HTTP   ┌────────────┐
│  Pedidos    │──────────▶│   Cardápio   │          │ Pagamento  │
│  :8002      │           │   :8001      │          │  :8003     │
└─────────────┘           └──────────────┘          └─────┬──────┘
       ▲                                                   │
       │ HTTP PATCH /status                                │ AMQP publish
       └───────────────────────────────────────────────────┘
                                                           │
                                                    ┌──────▼──────┐
                                                    │  RabbitMQ   │
                                                    │  fila:      │
                                                    │  pedido.pago│
                                                    └──────┬──────┘
                                                           │ AMQP consume
                                                    ┌──────▼──────┐
                                                    │ Notificação │
                                                    │  :8004      │
                                                    └─────────────┘
```

### Comunicação
| Origem | Destino | Tipo |
|---|---|---|
| Pedidos → Cardápio | `GET /cardapio/{id}` | HTTP síncrono |
| Pagamento → Pedidos | `GET /pedidos/{id}` + `PATCH /pedidos/{id}/status` | HTTP síncrono |
| Pagamento → Notificação | fila `pedido.pago` | AMQP assíncrono (RabbitMQ) |

### Bancos de dados
Cada serviço tem seu **próprio banco SQLite** em volume Docker isolado — nenhum banco é compartilhado.

---

## Como rodar

```bash
# Subir tudo
docker-compose up --build

# Subir em background
docker-compose up --build -d

# Ver logs de um serviço específico
docker-compose logs -f servico-pagamento

# Parar tudo
docker-compose down
```

### Portas
| Serviço | Porta local |
|---|---|
| Cardápio | http://localhost:8001/docs |
| Pedidos | http://localhost:8002/docs |
| Pagamento | http://localhost:8003/docs |
| Notificação | http://localhost:8004/docs |
| RabbitMQ UI | http://localhost:15672 (lanchonete / lanchonete123) |

---

## Fluxo completo (curl)

```bash
# 1. Criar item no cardápio
curl -X POST http://localhost:8001/cardapio/ \
  -H "Content-Type: application/json" \
  -d '{"nome": "X-Burguer", "preco": 18.50}'

# 2. Criar pedido
curl -X POST http://localhost:8002/pedidos/ \
  -H "Content-Type: application/json" \
  -d '{"cliente": "João", "itens": [{"item_cardapio_id": 1, "quantidade": 2}]}'

# 3. Processar pagamento
curl -X POST http://localhost:8003/pagamento/processar \
  -H "Content-Type: application/json" \
  -d '{"pedido_id": 1}'

# 4. Verificar notificação da cozinha
curl http://localhost:8004/notificacoes/1

# 5. Health checks
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

## Fluxo completo de testes no Swagger

Cada serviço expõe a documentação automática do FastAPI em `/docs`. O fluxo abaixo
é o caminho recomendado para testar a solução ponta a ponta sem usar `curl`.

### 1. Cardápio

Abra [http://localhost:8001/docs](http://localhost:8001/docs) e execute:

1. `GET /health` para validar que o serviço subiu.
2. `POST /cardapio/` com este corpo:

```json
{
  "nome": "X-Burguer",
  "descricao": "Sanduíche principal do teste",
  "preco": 18.5,
  "disponivel": true
}
```

3. Anote o `id` retornado, porque ele será usado no serviço de Pedidos.
4. `GET /cardapio/` para confirmar que o item foi persistido.

Resultado esperado: `201 Created` no cadastro e `200 OK` na listagem.

### 2. Pedidos

Abra [http://localhost:8002/docs](http://localhost:8002/docs) e execute:

1. `GET /health`.
2. `POST /pedidos/` com o `id` do item criado no Cardápio:

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

3. `GET /pedidos/{pedido_id}` para conferir o pedido criado.
4. `GET /pedidos/` para validar a listagem.

Resultado esperado: o pedido nasce com status `PENDENTE` e valor total calculado.

### 3. Pagamento

Abra [http://localhost:8003/docs](http://localhost:8003/docs) e execute:

1. `GET /health`.
2. `POST /pagamento/processar` com o `pedido_id` criado no passo anterior:

```json
{
  "pedido_id": 1
}
```

3. `GET /pagamento/{pedido_id}/status` para validar o registro do pagamento.

Resultado esperado: `201 Created`, pagamento aprovado e status do pedido atualizado para `ENVIADO_COZINHA`.

### 4. Notificação

Abra [http://localhost:8004/docs](http://localhost:8004/docs) e execute:

1. `GET /health`.
2. `GET /notificacoes/{pedido_id}` para confirmar a mensagem da cozinha.
3. `GET /notificacoes/` para validar a listagem completa.

Resultado esperado: a notificação aparece depois que o pagamento publica o evento na fila.

### 5. Cenários negativos que devem ser testados no Swagger

1. `POST /pedidos/` com `item_cardapio_id` inexistente deve retornar `404`.
2. `POST /pedidos/` com `itens: []` deve retornar `400`.
3. `POST /pagamento/processar` com `pedido_id` inexistente deve retornar `404`.
4. `POST /pagamento/processar` para pedido já pago deve retornar `400` ou `409`, dependendo do estado atual.
5. `DELETE /pedidos/{pedido_id}` para pedido pago deve retornar `400`.

### Ordem recomendada de execução

1. Cardápio.
2. Pedidos.
3. Pagamento.
4. Notificação.
5. Cenários negativos.
---

## ✅ Checklist

- [x] 4 serviços em portas distintas (8001–8004), cada um com banco isolado
- [x] Docker Compose orquestrando tudo com healthchecks
- [x] Fluxo pedido → pagamento via HTTP síncrono
- [x] Notificação de cozinha via fila assíncrona (RabbitMQ)
- [x] Cada serviço tem `GET /health` próprio
- [x] Estratégia de resiliência: **retry com backoff** (tenacity, 3 tentativas, espera 1s) em todas as chamadas HTTP entre serviços
- [x] Experimento obrigatório documentado abaixo
- [x] Rollback de pagamento documentado abaixo

---

## 🧪 Experimento Obrigatório — Derrubar o serviço de Notificação

```bash
# 1. Suba tudo normalmente
docker-compose up -d

# 2. Crie um item e um pedido (passos 1 e 2 do fluxo acima)

# 3. DERRUBE o serviço de notificação
docker-compose stop servico-notificacao

# 4. Processe o pagamento
curl -X POST http://localhost:8003/pagamento/processar \
  -H "Content-Type: application/json" \
  -d '{"pedido_id": 1}'
```

### O que acontece

| Componente | Comportamento |
|---|---|
| `POST /pagamento/processar` | ✅ Retorna 201 — pagamento registrado com sucesso |
| Status do pedido | ✅ Atualizado para `ENVIADO_COZINHA` via HTTP a Pedidos |
| Notificação | ⏳ Mensagem publicada na fila RabbitMQ — **fica acumulada** |
| `GET /notificacoes/1` | ❌ 404 — serviço offline, mas pagamento já completou |

```bash
# 5. Volte o serviço de notificação
docker-compose start servico-notificacao

# 6. O consumer processa automaticamente as mensagens acumuladas
docker-compose logs -f servico-notificacao
# [COZINHA] Pedido #1 do cliente 'João' pago — iniciar preparo!

# 7. Agora a notificação aparece
curl http://localhost:8004/notificacoes/1
```

### Conclusão

O pagamento **nunca falha** por causa da notificação. A fila desacopla os serviços no tempo — consistência eventual. Isso não seria possível no monólito sem mudanças arquiteturais significativas.

---

## 🔄 Rollback apenas do serviço de Pagamento

### Estratégia com Docker Compose

```bash
# 1. Verificar imagens disponíveis
docker images | grep pagamento

# 2. Rollback: subir versão anterior da imagem sem afetar outros serviços
docker-compose stop servico-pagamento
docker-compose rm -f servico-pagamento

# Editar docker-compose.yml: trocar build por image: pagamento:v1.0
# ou usar variável de ambiente:
PAGAMENTO_IMAGE=lanchonete-servico-pagamento:v1.0 docker-compose up -d servico-pagamento

# 3. Verificar que os outros serviços não foram afetados
curl http://localhost:8001/health  # cardápio: ok
curl http://localhost:8002/health  # pedidos: ok
curl http://localhost:8004/health  # notificação: ok
```

### Por que funciona no microsserviço e não no monólito

No monólito, um rollback significa regredir **toda a aplicação**. Se Cardápio recebeu
mudanças junto com Pagamento, voltar Pagamento significa perder Cardápio também.

Nos microsserviços, cada serviço tem seu próprio ciclo de deploy. O contrato de API
(endpoints e schemas) é o único ponto de compatibilidade. Enquanto
`POST /pagamento/processar` aceitar `{"pedido_id": int}` e retornar os mesmos campos,
o rollback é transparente para os demais serviços.

**Cuidado com migrações de banco:** se a versão nova adicionou colunas ao banco de
Pagamento, o rollback pode precisar de uma migration de reversão antes de trocar a imagem.

---

## 🛡️ Resiliência implementada: Retry com backoff

Localização: `servico-pedidos/app/main.py` e `servico-pagamento/app/main.py`

```python
@retry(
    stop=stop_after_attempt(3),   # máximo 3 tentativas
    wait=wait_fixed(1),            # espera 1s entre tentativas
    retry=retry_if_exception_type(httpx.RequestError),  # só em falhas de rede
)
def buscar_item_cardapio(item_id: int) -> dict:
    ...
```

Isso cobre falhas transitórias de rede (timeout, conexão recusada).
Para produção, recomenda-se adicionar **circuit breaker** (ex: biblioteca `pybreaker`)
para parar de tentar quando o serviço destino está claramente fora do ar.
