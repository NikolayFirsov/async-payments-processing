# Асинхронный сервис процессинга платежей

Микросервис принимает запросы на оплату, обрабатывает их асинхронно через эмуляцию платёжного шлюза и уведомляет клиента о результате через webhook.

**Стек:** FastAPI + Pydantic v2, SQLAlchemy 2.0 (async, asyncpg), PostgreSQL, RabbitMQ (FastStream), Alembic, Docker.

## Запуск

```bash
docker compose up --build
```

Поднимаются: `postgres`, `rabbitmq` (UI: http://127.0.0.1:15672, guest/guest), `migrate` (одноразово применяет Alembic), `api` (http://127.0.0.1:8000, Swagger: `/docs`), `consumer`.

API-ключ по умолчанию `change-me`

## Примеры

Для проверки webhook удобно взять https://webhook.site

**Создание платежа**

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/payments \
  -H "X-API-Key: change-me" \
  -H "Idempotency-Key: 123" \
  -H "Content-Type: application/json" \
  -d '{
        "amount": "1500.00",
        "currency": "RUB",
        "description": "Оплата заказа #777",
        "metadata": {"order_id": 777, "customer": "ivan"},
        "webhook_url": "https://webhook.site/<your-uuid>"
      }'
```

```
HTTP/1.1 202 Accepted
{"payment_id":"7c1f...","status":"pending","created_at":"2026-10-22T12:30:30.524204Z"}
```

При использовании того же `Idempotency-Key` вернётся тот же `payment_id`, новый платёж не создаётся.

**Получение платежа**

```bash
curl http://127.0.0.1:8000/api/v1/payments/<payment_id> -H "X-API-Key: change-me"
```

```json
{
  "payment_id": "7c1f...",
  "amount": "1500.00",
  "currency": "RUB",
  "description": "Оплата заказа #777",
  "metadata": {"order_id": 777, "customer": "ivan"},
  "status": "succeeded",
  "idempotency_key": "123",
  "webhook_url": "https://webhook.site/<your-uuid>",
  "created_at": "2026-10-22T12:30:30.524204Z",
  "processed_at": "2026-10-22T12:30:35.012345Z"
}
```

**Webhook (POST на `webhook_url`)**

```json
{
  "payment_id": "7c1f...",
  "status": "succeeded",
  "amount": "1500.00",
  "currency": "RUB",
  "description": "Оплата заказа #777",
  "metadata": {"order_id": 777, "customer": "ivan"},
  "created_at": "...",
  "processed_at": "..."
}
```

Коды ответов: `401` — нет/неверный `X-API-Key`; `422` — невалидное тело или нет `Idempotency-Key`; `409` — `Idempotency-Key` уже использован с другим телом; `404` — платёж не найден.

## Проверка retry и DLQ

Укажите заведомо недоступный `webhook_url`. Платёж получит финальный статус, а webhook будет повторён через 2 и 4 секунды; после третьей неудачи сообщение окажется в очереди `payments.new.dlq` (видно в RabbitMQ UI -> Queues).
