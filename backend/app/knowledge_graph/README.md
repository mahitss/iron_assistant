# Kairo Personal Knowledge Graph & Relationship Memory Engine (Task 50)

The Personal Knowledge Graph & Relationship Memory Engine builds a structured, temporal, provenance-aware graph representing authorized relationships among users, people, projects, organizations, repositories, files, documents, tasks, goals, decisions, conversations, messages, meetings, devices, applications, services, deployments, environments, events, preferences, skills, knowledge, and outcomes.

---

## 1. Core Architecture & Pipeline

```text
OBSERVATION
   ↓
EXTRACT ENTITY / RELATIONSHIP
   ↓
VALIDATE (Collision Defense, Integrity)
   ↓
ATTACH PROVENANCE (Source Reference)
   ↓
SCOPE (Private, Project, Org, Global)
   ↓
STORE (Nodes, Edges, Assertions, Decisions)
   ↓
RETRIEVE (Structural, Semantic, Temporal As-Of, Bounded Traversal)
   ↓
REASON (Contradiction Detection & Domain Authority Reconciliation)
   ↓
VERIFY (Fact Validation, Grounded Summaries)
   ↓
UPDATE (Controlled Forgetting, Snapshot Versioning)
```

---

## 2. Invariants & Security Rules

1. **Memory is NOT Truth**: Confidence is not proof. Inferences are not automatically memories, and graph edges are not automatically facts. Inferred nodes/edges are explicitly marked and never stored as "known" without validation.
2. **Current Instruction Strict Override**: Current explicit user instructions always override older preferences and memories.
3. **Temporal Validity & History Preservation**: Facts change over time. Historical state is preserved with `valid_from` / `valid_until` windows and point-in-time "as-of" querying rather than silently overwriting past knowledge.
4. **No Unrestricted Social Surveillance or Sensitive Profiling**: People entities and relationship graphs represent work and authorized context only. Sensitive personal attributes (religion, politics, sexual orientation, health, psychological traits) are strictly barred from inference or storage.
5. **Controlled Forgetting & Propagation**: Users can request deletion of eligible memories across single facts, entities, relationships, or categories. Forgetting propagates to derived indexes while auditing deletions without retaining sensitive content.
6. **Zero Memory Poisoning & Injection**: Graph content is structured data, not executable instructions. Untrusted external/web inputs cannot directly forge durable trusted memories. Secrets are detected and redacted before persistence.
7. **Strict Multi-Tenant & Project Isolation**: Private memories never leak between users, projects, or organizations.
