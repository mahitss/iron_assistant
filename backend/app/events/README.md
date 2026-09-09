# Kairo Event Bus Engine (`app.events`)

The internal event-driven runtime powering decoupled subsystem coordination, failure isolation, and secure asynchronous messaging in Kairo.

## Module Structure

- `schemas.py`: Canonical `Event` model, `EventSource`, `EventStatus`, and `ReplaySafety` enums.
- `registry.py`: Central catalog of registered event types, versioning, descriptions, and retention policies.
- `safety.py`: Security authority enforcement, prompt injection defense, and credential redaction.
- `dedup.py`: Sliding-window event deduplicator tracking seen event IDs and domain idempotency keys.
- `retry.py`: Exponential backoff policies differentiating transient from permanent delivery failures.
- `dead_letter.py`: Dead letter storage, error traceback sanitization, and guarded replay enforcement.
- `dispatcher.py`: Bounded worker queue, priority ordering, backpressure, and failure isolation.
- `publisher.py`: Secure publication pipeline with lineage tracking (`correlation_id`, `causation_id`).
- `subscriber.py`: EventSubscriber with pattern matching (`*`, `github.*`), priority, and tenant boundaries.
- `outbox.py`: Transactional outbox staging and background OutboxProcessor.
- `metrics.py`: Telemetry store tracking throughput, latency percentiles, retry rates, and queue size.
- `models.py`: SQLAlchemy database models (`events`, `event_outbox`, `dead_letter_events`).
- `db.py`: Non-blocking async database session acquisition helper.
- `handlers/`: Default system subscribers:
  - `knowledge_handler.py`: Context and knowledge ingestion.
  - `proactive_handler.py`: Proactive remediation suggestions.
  - `notification_handler.py`: Real-time user alerts.
  - `security_handler.py`: Tamper-evident AuditLogger routing.
  - `activity_handler.py`: User-facing activity timeline formatter.
