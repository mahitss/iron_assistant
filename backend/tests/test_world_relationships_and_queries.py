"""Tests for World Model relationships, graph traversal, and structured queries (Task 32, Spec 22-24, 38-42, 98-100)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.world.entities import (
    ConfidenceLevel,
    EntityType,
    ObservationType,
    WorldEntitySchema,
)
from app.world.queries import WorldQueryEngine
from app.world.relationships import (
    RelationshipType,
    WorldRelationshipSchema,
    generate_relationship_id,
)


@pytest.fixture
def sample_world_graph():
    """Build a sample entity and relationship graph."""
    now = datetime.now(UTC)
    user_id = "user_test"

    proj = WorldEntitySchema(
        id="ent_proj_1",
        type=EntityType.PROJECT,
        name="Kairo Core",
        owner_id=user_id,
        project_id="proj_1",
        source="projects",
        source_id="proj_1",
        state="ACTIVE",
        observed_at=now,
    )

    repo = WorldEntitySchema(
        id="ent_repo_1",
        type=EntityType.REPOSITORY,
        name="kairo-repo",
        owner_id=user_id,
        project_id="proj_1",
        source="github",
        source_id="repo_1",
        state="SYNCED",
        observed_at=now,
    )

    svc_api = WorldEntitySchema(
        id="ent_svc_api",
        type=EntityType.SERVICE,
        name="api-service",
        owner_id=user_id,
        project_id="proj_1",
        source="observability",
        source_id="svc_api",
        state="HEALTHY",
        observed_at=now,
        metadata={"environment": "development"},
    )

    svc_db = WorldEntitySchema(
        id="ent_svc_db",
        type=EntityType.SERVICE,
        name="postgres-db",
        owner_id=user_id,
        project_id="proj_1",
        source="observability",
        source_id="svc_db",
        state="HEALTHY",
        observed_at=now,
        metadata={"environment": "development"},
    )

    task = WorldEntitySchema(
        id="ent_task_1",
        type=EntityType.TASK,
        name="Task: Fix CI",
        owner_id=user_id,
        project_id="proj_1",
        source="task_engine",
        source_id="task_1",
        state="RUNNING",
        observed_at=now,
    )

    dev = WorldEntitySchema(
        id="ent_dev_1",
        type=EntityType.DEVICE,
        name="Workstation",
        owner_id=user_id,
        project_id=None,
        source="local_companion",
        source_id="dev_1",
        state="CONNECTED",
        observed_at=now,
    )

    entities = [proj, repo, svc_api, svc_db, task, dev]

    # Relationships: Proj -> Repo, Proj -> Task, SvcAPI -> SvcDB (dependency), Proj -> SvcAPI
    rel1 = WorldRelationshipSchema(
        id="rel_1",
        source_entity_id=proj.id,
        target_entity_id=repo.id,
        relationship_type=RelationshipType.CONTAINS,
        owner_id=user_id,
    )
    rel2 = WorldRelationshipSchema(
        id="rel_2",
        source_entity_id=svc_api.id,
        target_entity_id=svc_db.id,
        relationship_type=RelationshipType.DEPENDS_ON,
        owner_id=user_id,
    )
    rel3 = WorldRelationshipSchema(
        id="rel_3",
        source_entity_id=proj.id,
        target_entity_id=svc_api.id,
        relationship_type=RelationshipType.USES,
        owner_id=user_id,
    )

    relationships = [rel1, rel2, rel3]
    return entities, relationships


def test_relationship_identity_generation():
    """Verify deterministic relationship edge IDs (Spec 22)."""
    id1 = generate_relationship_id("ent_a", "ent_b", RelationshipType.DEPENDS_ON)
    id2 = generate_relationship_id("ent_a", "ent_b", RelationshipType.DEPENDS_ON)
    id3 = generate_relationship_id("ent_a", "ent_b", RelationshipType.CONTAINS)

    assert id1 == id2
    assert id1 != id3
    assert id1.startswith("rel_")


def test_get_project_state_query(sample_world_graph):
    """Verify get_project_state aggregates repositories, tasks, and services (Spec 38)."""
    entities, relationships = sample_world_graph
    data = WorldQueryEngine.get_project_state("proj_1", "user_test", entities, relationships)

    assert data["project"] is not None
    assert data["project"]["name"] == "Kairo Core"
    assert len(data["repositories"]) == 1
    assert len(data["tasks"]) == 1
    assert len(data["services"]) == 2


def test_get_active_tasks_query(sample_world_graph):
    """Verify active task filtering excludes completed/failed tasks (Spec 38)."""
    entities, _ = sample_world_graph
    active_tasks = WorldQueryEngine.get_active_tasks("user_test", "proj_1", entities)

    assert len(active_tasks) == 1
    assert active_tasks[0].id == "ent_task_1"
    assert active_tasks[0].state == "RUNNING"


def test_get_connected_devices_query(sample_world_graph):
    """Verify connected devices filtering (Spec 38)."""
    entities, _ = sample_world_graph
    devices = WorldQueryEngine.get_connected_devices("user_test", entities)

    assert len(devices) == 1
    assert devices[0].id == "ent_dev_1"
    assert devices[0].state == "CONNECTED"


def test_get_dependencies_bounded_traversal(sample_world_graph):
    """Verify bounded dependency traversal with BFS and visited tracking (Spec 41, 42, 100)."""
    entities, relationships = sample_world_graph
    entities_by_id = {e.id: e for e in entities}

    # Query dependencies for svc_api -> should find svc_db
    deps = WorldQueryEngine.get_dependencies(
        entity_id="ent_svc_api",
        user_id="user_test",
        entities_by_id=entities_by_id,
        relationships=relationships,
        max_depth=3,
    )

    assert deps["root"] is not None
    assert deps["root"]["id"] == "ent_svc_api"
    assert len(deps["dependencies"]) == 1
    assert deps["dependencies"][0]["id"] == "ent_svc_db"
    assert len(deps["edges"]) == 1


def test_dependency_cycle_safety():
    """Verify circular dependency graph does not trigger infinite recursion (Spec 42)."""
    now = datetime.now(UTC)
    ent_a = WorldEntitySchema(id="ent_a", type=EntityType.SERVICE, name="A", owner_id="u1", source="sys", source_id="a", state="OK", observed_at=now)
    ent_b = WorldEntitySchema(id="ent_b", type=EntityType.SERVICE, name="B", owner_id="u1", source="sys", source_id="b", state="OK", observed_at=now)

    # Circular edges: A -> B -> A
    rel_ab = WorldRelationshipSchema(id="r1", source_entity_id="ent_a", target_entity_id="ent_b", relationship_type=RelationshipType.DEPENDS_ON, owner_id="u1")
    rel_ba = WorldRelationshipSchema(id="r2", source_entity_id="ent_b", target_entity_id="ent_a", relationship_type=RelationshipType.DEPENDS_ON, owner_id="u1")

    entities_by_id = {"ent_a": ent_a, "ent_b": ent_b}
    deps = WorldQueryEngine.get_dependencies("ent_a", "u1", entities_by_id, [rel_ab, rel_ba], max_depth=3)

    # Should safely terminate without recursion error
    assert deps["root"]["id"] == "ent_a"
    assert len(deps["dependencies"]) == 1
    assert deps["dependencies"][0]["id"] == "ent_b"


def test_get_recent_changes_query(sample_world_graph):
    """Verify domain changes filtering within time window (Spec 98, 99)."""
    entities, _ = sample_world_graph
    ten_minutes_ago = datetime.now(UTC) - timedelta(minutes=10)

    changes = WorldQueryEngine.get_recent_changes(ten_minutes_ago, "user_test", entities)
    assert len(changes) == len(entities)
    assert all("summary" in c for c in changes)
