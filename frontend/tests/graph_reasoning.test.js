/**
 * Unit tests for Task 97: KAIRO Autonomous Knowledge Graph Reasoning, Graph Memory & Structured Inference UI.
 * Verifies GraphReasoningView initialization, template rendering, tab switching,
 * entity inspection, impact analysis simulation, and lineage reconstruction.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import { GraphReasoningView } from '../components/knowledge_graph/graphReasoningView.js';

describe('GraphReasoningView Component (Task 97 UI)', () => {
  function createMockContainer() {
    let containerHtml = '';
    const elements = new Map();

    const container = {
      get innerHTML() {
        return containerHtml;
      },
      set innerHTML(val) {
        containerHtml = val;
      },
      querySelectorAll: (sel) => {
        return [];
      },
      querySelector: (sel) => {
        if (!elements.has(sel)) {
          let elHtml = '';
          elements.set(sel, {
            get innerHTML() {
              return elHtml;
            },
            set innerHTML(val) {
              elHtml = val;
            },
            style: {},
            classList: {
              add: () => {},
              remove: () => {},
              toggle: () => {},
            },
            addEventListener: () => {},
          });
        }
        return elements.get(sel);
      },
      addEventListener: () => {},
    };
    return container;
  }

  function createMockApi() {
    const mockNodes = [
      {
        node_id: 'srv_db_postgres',
        canonical_key: 'service:db:postgres',
        node_type: 'SERVICE',
        label: 'Production PostgreSQL Cluster',
        certainty: 'KNOWN',
        confidence: 1.0,
        status: 'ACTIVE',
        provenance: { classification: 'SYSTEM_VERIFIED', extraction_method: 'INFRASTRUCTURE' }
      },
      {
        node_id: 'cap_etl_pipeline',
        canonical_key: 'capability:etl:pipeline',
        node_type: 'CAPABILITY',
        label: 'Continuous ETL Ingestion',
        certainty: 'KNOWN',
        confidence: 0.95,
        status: 'ACTIVE',
        provenance: { classification: 'OBSERVED', extraction_method: 'TELEMETRY' }
      }
    ];

    return {
      listNodes: async () => ({ nodes: mockNodes, total_count: 2 }),
      getNode: async (id) => mockNodes.find(n => n.node_id === id) || mockNodes[0],
      getNeighbors: async () => ({ outgoing: [], incoming: [] }),
      getDependencies: async (id) => ({
        node_id: id,
        dependencies: [
          { source_node: 'cap_etl_pipeline', target_node: 'srv_db_postgres', relationship_type: 'DEPENDS_ON', confidence: 0.95 }
        ]
      }),
      getDependents: async (id) => ({
        node_id: id,
        dependents: [
          { source_node: 'cap_etl_pipeline', target_node: 'srv_db_postgres', relationship_type: 'DEPENDS_ON', confidence: 0.95 }
        ]
      }),
      analyzeImpact: async ({ origin_node, max_depth }) => ({
        origin_node,
        max_propagation_depth: 2,
        total_impacted_nodes: 1,
        overall_risk_severity: 'MEDIUM',
        impacted_nodes: [
          { node_id: 'cap_etl_pipeline', node_type: 'CAPABILITY', depth: 1, confidence: 0.95, criticality: 'HIGH' }
        ],
        revalidation_candidates: ['cap_etl_pipeline']
      }),
      reconstructDecision: async (id) => ({
        target_node: id,
        lineage_type: 'decision',
        summary: 'Goal -> Decision -> Action -> Outcome',
        steps: [
          { node_id: 'goal_01', node_type: 'GOAL', relationship: 'ROOT' },
          { node_id: id, node_type: 'DECISION', relationship: 'DECIDED_BY' }
        ]
      }),
      findPath: async ({ source_node, target_node }) => ({
        source_node,
        target_node,
        path_found: true,
        path: [
          { node_id: source_node, edge: { relationship_type: 'DEPENDS_ON' } },
          { node_id: target_node, edge: null }
        ]
      }),
      runInference: async () => ({
        derived_edges: [
          { source_node: 'wf_etl', target_node: 'srv_db', relationship_type: 'TRANSITIVELY_DEPENDS_ON', derivation_rule: 'RULE_TRANSITIVE_DEPENDS_ON' }
        ]
      }),
      listConflicts: async () => ({
        conflicts: [
          { node_a: 'mem_fact_1', node_b: 'mem_fact_2', status: 'UNRESOLVED', reason: 'Value discrepancy' }
        ]
      }),
      listSnapshots: async () => ({
        snapshots: [
          { snapshot_id: 'snap_20260916', label: 'Baseline', node_count: 2, edge_count: 1 }
        ]
      }),
      computeDiff: async () => ({
        base_snapshot_id: 'snap_1',
        target_snapshot_id: 'snap_2',
        added_nodes: ['srv_cache'],
        removed_nodes: [],
        changed_nodes: [],
        added_edges: [],
        removed_edges: []
      }),
      validateGraph: async () => ({
        is_consistent: true,
        orphan_count: 0,
        cycle_issues: [],
        contradictions: []
      })
    };
  }

  test('Instantiates with default state', () => {
    const container = createMockContainer();
    const view = new GraphReasoningView({ container });
    assert.strictEqual(view.state.activeTab, 'explorer');
    assert.strictEqual(Array.isArray(view.state.nodes), true);
    assert.strictEqual(view.state.selectedNode, null);
  });

  test('Renders markup with header, KPIs, tabs, and explorer content', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new GraphReasoningView({ container, api });

    await view.render();

    assert.ok(container.innerHTML.includes('Knowledge Graph Reasoning & Relationship Intelligence'));
    assert.ok(container.innerHTML.includes('TOTAL ENTITIES'));
    assert.ok(container.innerHTML.includes('Graph Explorer'));
    const tabArea = container.querySelector('#graph-tab-content');
    assert.ok(tabArea.innerHTML.includes('Production PostgreSQL Cluster'));
    assert.strictEqual(view.state.nodes.length, 2);
    assert.strictEqual(view.state.conflicts.length, 1);
  });

  test('Switches tabs and renders detail view for selected node', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new GraphReasoningView({ container, api });

    await view.render();
    await view.inspectNode('srv_db_postgres');

    assert.strictEqual(view.state.activeTab, 'detail');
    assert.strictEqual(view.state.selectedNodeId, 'srv_db_postgres');
    assert.ok(container.innerHTML.includes('SERVICE'));
  });

  test('Performs impact analysis simulation', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new GraphReasoningView({ container, api });

    await view.render();
    await view.runImpactAnalysis('srv_db_postgres', 3);

    assert.notStrictEqual(view.state.impactResult, null);
    assert.strictEqual(view.state.impactResult.overall_risk_severity, 'MEDIUM');
    assert.strictEqual(view.state.impactResult.total_impacted_nodes, 1);
  });

  test('Performs decision lineage reconstruction', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new GraphReasoningView({ container, api });

    await view.render();
    await view.runLineageReconstruction('decision', 'dec_infra_01');

    assert.notStrictEqual(view.state.lineageResult, null);
    assert.strictEqual(view.state.lineageResult.lineage_type, 'decision');
    assert.strictEqual(view.state.lineageResult.steps.length, 2);
  });

  test('Executes shortest verified path and deductive inference', async () => {
    const container = createMockContainer();
    const api = createMockApi();
    const view = new GraphReasoningView({ container, api });

    await view.render();
    await view.findPath('srv_db', 'cap_etl');
    await view.triggerInference();

    assert.strictEqual(view.state.metrics.activeInferences >= 1, true);
  });
});
