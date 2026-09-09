# Kairo Long-Term Experience and Learning Subsystem (Task 29)

The Kairo Long-Term Experience and Learning Subsystem provides a controlled, bounded, explainable, traceable, and reversible learning loop.

## Core Principle

```
event
  ↓
candidate learning
  ↓
validation & safety guardrails
  ↓
confidence scoring
  ↓
user & system policy
  ↓
stored experience
  ↓
future retrieval
```

**Never**:
```
event
  ↓
"learn forever" (autonomous model rewriting / policy mutation)
```

## Architectural Distinction

- **Memory**: Persistent factual statements Kairo should explicitly remember (`memories` table).
- **Experience**: Structured, bounded metadata of what happened while Kairo performed tasks (`experiences` table).
- **Preference**: Explicit declarations of how the user wants Kairo to behave, scoped safely (`preferences` table).
- **Knowledge Fabric**: Extracted entities, facts, documentation, code, and decisions in the knowledge graph.
- **Evaluation**: Controlled benchmark test cases used to measure and validate future model/skill versions.

## Strict Security & Privacy Invariants

1. **No Autonomous Policy Mutations**: Experience, candidates, or feedback **CANNOT** modify `SecurityCenter`, `Permissions`, approval requirements, tool allowlists, skill risk tiers, device authorizations, or emergency stops.
2. **No Autonomous Code/Prompt Modifications**: System instructions, prompts, and production code cannot be modified autonomously based solely on experience.
3. **Anti-Prompt Injection**: External web pages and untrusted inputs can **NEVER** create durable user preferences or experiences.
4. **Zero Sensitive Profiling**: Inferences regarding psychological traits, political affiliations, religious beliefs, sexual orientation, health conditions, or racial/ethnic backgrounds are strictly blocked.
5. **Scoped User Corrections**: User corrections receive `HIGH` confidence and narrow scope (default `PROJECT`), overriding older inferred behavior within their scope without overgeneralizing.
6. **Provenance & Supersession**: When new explicit preferences or corrections are made, prior conflicting active records are transitioned to `SUPERSEDED`, never silently deleted.
7. **Decay on Evolution**: When projects undergo repository updates or migrations, related experiences are marked `STALE` and subject to re-verification.

## Controlled Improvement Loop

```
Experience / Task Failure
  ↓
Learning Candidate (PROPOSED)
  ↓
Evaluation Dataset (Scenario / Benchmark)
  ↓
Human / Engineering Review (ACCEPTED / REJECTED)
  ↓
Code / Config Change
  ↓
CI & Regression Benchmark
  ↓
Controlled Release
```

## REST API Endpoints

- `POST /api/v1/feedback`: Submit user feedback (positive, negative, correction, rating, comment).
- `GET /api/v1/feedback`: List own user feedback (tenant-isolated).
- `GET /api/v1/experience`: Search and filter experiences (project, type, status, scope).
- `GET /api/v1/experience/{id}`: Retrieve single experience detail.
- `POST /api/v1/experience/corrections`: Submit explicit scoped user correction.
- `POST /api/v1/experience/preferences`: Store explicit user/project preference.
- `GET /api/v1/experience/preferences`: List active preferences.
- `DELETE /api/v1/experience/preferences/{key}`: Delete user preference.
- `POST /api/v1/experience/{id}/supersede`: Mark experience superseded by newer one.
- `DELETE /api/v1/experience/{id}`: Delete user experience record.
- `GET /api/v1/experience/export`: Safe structured export of memory, preferences, and experiences.
- `POST /api/v1/experience/candidates`: Propose learning candidate.
- `GET /api/v1/experience/candidates`: List candidates for engineering review.
- `POST /api/v1/experience/candidates/{id}/review`: Accept/reject learning candidate.
- `GET /api/v1/experience/analytics/failures`: Aggregated failure analytics.
- `GET /api/v1/experience/analytics/successes`: Aggregated success analytics.
