# Kairo World Model Subsystem

The **Kairo World Model** maintains a bounded, current representation of the environment Kairo is authorized to observe.

## Core Principle

> **"What Kairo currently believes about authorized entities and their state."**

The World Model is a synchronized projection, **not** the source of truth:
- **GitHub** is authoritative for repository state.
- **Database** is authoritative for application records.
- **Local Companion** is authoritative for device runtime.
- **SecurityCenter** is authoritative for permissions.
- **Observability** is authoritative for service health.

## Module Structure

- `entities.py`: Canonical entity types and Pydantic schemas.
- `relationships.py`: Typed directed edges between entities.
- `state.py`: Validated lifecycle states and transition matrices.
- `freshness.py`: Freshness policy and staleness evaluator.
- `registry.py`: Source-of-truth registry and authority hierarchy.
- `conflicts.py`: Conflict detection and authoritative reconciliation.
- `snapshots.py`: Bounded point-in-time state snapshots.
- `queries.py`: Structured graph queries with depth budget.
- `policies.py`: Security, privacy, anti-surveillance, and anti-injection guards.
- `resolver.py`: World context packet builder for the Context Engine and Task Planner.
- `synchronizer.py`: Event-driven ingest and periodic reconciliation.
- `model.py`: Central `KairoWorldModel` engine facade.
