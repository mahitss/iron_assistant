# Kairo Knowledge Fabric

The **Kairo Knowledge Fabric** provides a unified, cross-domain knowledge orchestration and indexing layer that connects Projects, Conversations, Memories, Repositories, Documents, Web Research, Workflow Runs, Notifications, Agent Tasks, Devices, Tasks, and Decisions into an interconnected, queryable knowledge graph.

The Knowledge Fabric is designed according to a fundamental architectural principle:
> **Core Principle**: Do not create another independent memory system or vector database. The Knowledge Fabric is an orchestration and indexing layer built directly on top of existing PostgreSQL, pgvector, Memory, and Context Engine infrastructure.

---

## 1. Architecture

```
                 KAIRO CORE
                     │
              KNOWLEDGE FABRIC
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
   STRUCTURED     SEMANTIC      TEMPORAL
     DATA         SEARCH         CONTEXT
       │             │             │
       └─────────────┼─────────────┘
                     ↓
              KNOWLEDGE GRAPH
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
   PROJECTS      MEMORIES       SOURCES
       │             │             │
   REPOS        CONVERSATIONS   WEB
   WORKFLOWS    DOCUMENTS       AGENTS
   DEVICES      NOTIFICATIONS   EVENTS
```

The Knowledge Fabric coordinates four primary subsystem components:
1. **Normalized Entity Abstraction (`KnowledgeNode`)**: Represents discrete knowledge entities without storing sensitive secrets or credentials in metadata.
2. **Strict Typed Directed Graph (`KnowledgeEdge`)**: Connects nodes via allowlisted semantic relationships with confidence scoring and cycle-safe traversal.
3. **Multi-Strategy Hybrid Search Engine (`HybridSearchEngine`)**: Combines full-text lexical ranking, pgvector cosine similarity, recency decay (90-day half-life), and status penalties with Redis caching and graceful fallback.
4. **Temporal Context & Causality Reasoner (`TemporalReasoner`)**: Synthesizes chronological timelines and enforces evidence-based causality verification, strictly rejecting causality inferred from mere temporal proximity.

---

## 2. Knowledge Nodes

Every entity indexed into the fabric is represented as a normalized `KnowledgeNode`:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `String` (UUID) | Primary node identifier. |
| `user_id` | `String` | Multi-tenant owner identifier (strictly enforced). |
| `type` | `KnowledgeType` | Allowlisted entity category (e.g. `PROJECT`, `DECISION`, `MEMORY`, `DOCUMENT`). |
| `source_id` | `String` | Foreign identifier in authoritative source table or upstream system. |
| `project_id` | `String \| null` | Optional project scoping identifier. |
| `title` | `String` | Human-readable title or entity label. |
| `summary` | `String` | Concise synopsis for display, ranking, and synthesis. |
| `content` | `String \| null` | Bounded text excerpt for retrieval. |
| `embedding` | `Vector(1536) \| null` | Dense vector embedding for semantic search. |
| `status` | `String` | Lifecycle state (`ACTIVE`, `SUPERSEDED`, `ARCHIVED`, `DELETED`). |
| `confidence` | `Float` (0.0 - 1.0) | Ranking priority metadata (not absolute truth). |
| `node_metadata` | `JSONB` | Structured attributes (sanitized against secret keys). |
| `created_at` | `DateTime` (UTC) | Creation timestamp. |
| `updated_at` | `DateTime` (UTC) | Last modification timestamp. |
| `last_seen_at` | `DateTime` (UTC) | Timestamp when source last verified this fact. |

### Allowlisted Knowledge Types
The system strictly restricts node categories to 17 verified domain types:
- `PROJECT`, `CONVERSATION`, `MEMORY`, `DOCUMENT`
- `REPOSITORY`, `COMMIT`, `ISSUE`, `PULL_REQUEST`
- `WORKFLOW`, `WORKFLOW_RUN`, `AGENT_TASK`, `RESEARCH_RESULT`
- `WEB_SOURCE`, `NOTIFICATION`, `DEVICE`, `TASK`, `DECISION`

Arbitrary model-generated entity types are rejected at the schema validation boundary.

---

## 3. Relationships & Edges

Directed relationships connect nodes into a multi-dimensional semantic graph (`KnowledgeEdge`):

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `String` (UUID) | Edge identifier. |
| `user_id` | `String` | Multi-tenant owner identifier. |
| `source_node_id` | `String` | Outgoing node ID (must belong to same user). |
| `target_node_id` | `String` | Incoming node ID (must belong to same user). |
| `relation_type` | `KnowledgeRelationType` | Allowlisted relation enum. |
| `confidence` | `Float` | Connection certainty weight. |
| `source` | `String` | Upstream system or component that asserted edge. |
| `created_at` | `DateTime` (UTC) | Edge creation timestamp. |

### Allowlisted Relation Types
- `BELONGS_TO`: Entity belongs to a project or parent container.
- `RELATED_TO`: General semantic correlation.
- `DERIVED_FROM`: Document chunk derived from parent file; synthesis derived from source.
- `REFERENCES`: Explicit citation or cross-reference.
- `CREATED_BY`: Association with human user or agent task.
- `DEPENDS_ON`: Functional or system dependency.
- `CAUSED`: Verified empirical causal relationship (requires causal proof).
- `RESOLVES`: Commit or PR resolving an issue or workflow failure.
- `BLOCKS`: Task or issue preventing downstream progress.
- `MENTIONS`: Textual mention in conversation or summary.
- `OCCURRED_IN`: Event occurring within a project or environment.
- `LINKED_TO`: Association between devices, tasks, or workflows.
- `SUPERSEDES`: New architectural decision superseding older decision.
- `DUPLICATES`: Redundant or consolidated knowledge node.

---

## 4. Provenance & Source Hierarchy

External content is never accepted without explicit provenance tracking. Every indexed node references a verified entry in `knowledge_sources`:

```
Research Task ──► Source (URL / Doc) ──► Evidence Chunk ──► Answer
```

### Source Priority (Trust Ordering)
```
USER_EXPLICIT
      >
VERIFIED_FIRST_PARTY_SOURCE
      >
DIRECT_TOOL_RESULT
      >
CONVERSATION
      >
SYSTEM_DERIVED
```
*Note: Priority is used solely as ranking metadata during hybrid retrieval, never as uncritical dogma.*

---

## 5. Hybrid Search

The `HybridSearchEngine` provides deterministic multi-channel retrieval:

$$\text{Composite Score} = (0.40 \times \text{Vector} + 0.40 \times \text{Lexical} + 0.20 \times \text{Recency}) \times \text{Status Multiplier} \times \text{Confidence}$$

1. **Lexical Matching**: Exact and substring overlap across title and summary.
2. **Vector Cosine Similarity**: Cosine distance against 1536-dimensional embedding vectors.
3. **Recency Decay**: Linear decay over a 90-day window ($\max(0.1, 1.0 - \frac{\text{age\_days}}{90})$).
4. **Status Multiplier**: `SUPERSEDED` nodes receive a $0.4\times$ penalty, ensuring active decisions rank higher while preserving historical auditability.
5. **Embedding Failure Fallback**: If the embedding provider fails or pgvector is unavailable, the search engine transparently degrades to lexical and recency scoring without throwing user-facing 500 errors.
6. **Safe Redis Caching**: Search results are cached under user-scoped keys (`kairo:knowledge:search:{user_id}:{hash}`) with short TTLs and automatic invalidation on node mutations.

---

## 6. Graph Traversal

The `GraphTraversalService` provides bounded BFS and DFS traversals for contextual inspection:
- **Maximum Depth**: Configurable via `KAIRO_KNOWLEDGE_MAX_DEPTH` (default: 3).
- **Maximum Visited Nodes**: Bounded by `KAIRO_KNOWLEDGE_MAX_NODES` (default: 15).
- **Maximum Edges**: Bounded by `KAIRO_KNOWLEDGE_MAX_EDGES` (default: 20).
- **Cycle Prevention**: Visited node tracking prevents infinite loops on cyclic references (e.g. mutual `RELATED_TO` links).
- **Multi-Tenant Isolation**: Only edges where `user_id == current_user` are traversed.
- **Human Explanations**: Generates step-by-step path explanations (e.g. `"Kairo (PROJECT) -> [BELONGS_TO] -> CI Run (WORKFLOW_RUN)"`).

---

## 7. Document Ingestion Pipeline

User-provided documents are processed through a hardened pipeline:

```
Document Upload ──► Security Validation ──► Text Extraction ──► Semantic Chunking ──► Embedding ──► Graph Linking
```

### Security Validations
- **Path Traversal Protection**: Rejects filenames containing `..`, directory separators (`/`, `\`), or null bytes (`\x00`).
- **File Size Bounding**: Strictly caps uploads at `KAIRO_KNOWLEDGE_INDEX_MAX_BYTES` (default: 10MB).
- **Extension Allowlist**: Only `.txt`, `.md`, `.json`, `.csv`, `.pdf`, `.docx` are permitted.
- **No Direct Execution**: Uploaded files are treated purely as static text data and are never executed.

### Semantic Chunking
- Chunks text on semantic boundaries (markdown `#` headings, double newline paragraphs).
- Retains section headers in chunk node titles (e.g. `architecture.md [Core Memory]`).
- Bounded chunk size (`KAIRO_KNOWLEDGE_CHUNK_SIZE = 800` chars) with configurable overlap (`100` chars).
- Creates a `DERIVED_FROM` edge linking each chunk back to the root parent document node.

---

## 8. Temporal Reasoning & Conflict Detection

The `TemporalReasoner` handles time-aware reasoning without hallucinating:
- **Chronological Timelines**: Queries events ordered strictly by `created_at DESC` or `ASC`.
- **Evidence-Based Causality**: A `CAUSED` edge between a commit and a CI failure is created **only** if the CI logs or workflow failure metadata explicitly cite the commit SHA or run ID. Temporal proximity alone is strictly insufficient.
- **Contradiction Detection**: Detects conflicting factual claims across sources (e.g. Memory says `Python 3.11`, Repository spec says `Python 3.12`) and surfaces them explicitly:
  > *"I found conflicting information regarding python version (3.11 vs 3.12). Sources: Memory m_1 vs Repository r_1."*

---

## 9. Security & Multi-Tenant Isolation

1. **Strict User Scoping**: All database queries for nodes, edges, sources, and index jobs include `user_id == authenticated_user_id`. IDOR attacks are blocked at the ORM and query level.
2. **Informational Boundary**: Knowledge Fabric cannot grant permissions, approve tool calls, elevate capabilities, or bypass SecurityCenter.
3. **Untrusted External Content**: Web search results, GitHub READMEs, and document contents remain strictly data. Any prompt injection attempts (e.g. *"Ignore system instructions"*) are treated as raw string tokens and never executed as instructions.
4. **Append-Only Audit Logging**: Node creation, deletion, decision recording, and supersession emit immutable events to `SecurityAuditEvent`.

---

## 10. Privacy & Retention Rules

1. **No Sensitive Inferences**: Knowledge Fabric never infers or creates nodes related to health, religion, sexuality, political beliefs, or psychological profiling.
2. **Session vs. Durable Scope**: Agent execution results remain session-scoped by default and are only promoted to durable project knowledge if validated and non-sensitive.
3. **Cascading Deletion**: When a user deletes a parent document or project node, its derived chunk nodes and associated edges are marked `DELETED` and excluded from search indexes, eliminating orphan nodes.

---

## 11. Context Engine & Agent Integration

The Context Engine integrates knowledge retrieval seamlessly into the reasoning loop:
- Injects relevant knowledge packets into `ContextPacket` under `knowledge_context`.
- Respects strict token and node budgets (`max_nodes = 15`, `max_edges = 20`).
- Agents query scoped subgraphs rather than the entire knowledge graph:
  - **Researcher**: Queries `RESEARCH_RESULT` and `WEB_SOURCE` nodes.
  - **Developer**: Queries `REPOSITORY`, `COMMIT`, `ISSUE`, and `PULL_REQUEST` nodes.
  - **Supervisor**: Receives synthesized project and decision summaries.
