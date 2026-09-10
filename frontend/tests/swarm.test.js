/**
 * Unit tests for Kairo Collective Intelligence & Swarm Reasoning Engine (Task 64).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { endpoints, swarmApi } from '../lib/api/endpoints.js';
import { SwarmView } from '../components/swarm/swarmView.js';

describe('Collective Intelligence & Swarm Reasoning Endpoints (Task 64)', () => {
  test('Endpoints exposes all swarm methods', () => {
    assert.strictEqual(typeof endpoints.createSwarmSession, 'function');
    assert.strictEqual(typeof endpoints.listSwarmSessions, 'function');
    assert.strictEqual(typeof endpoints.getSwarmSession, 'function');
    assert.strictEqual(typeof endpoints.getSwarmAgents, 'function');
    assert.strictEqual(typeof endpoints.getSwarmTasks, 'function');
    assert.strictEqual(typeof endpoints.getSwarmResults, 'function');
    assert.strictEqual(typeof endpoints.getSwarmReviews, 'function');
    assert.strictEqual(typeof endpoints.getSwarmDisagreements, 'function');
    assert.strictEqual(typeof endpoints.getSwarmTimeline, 'function');
    assert.strictEqual(typeof endpoints.pauseSwarm, 'function');
    assert.strictEqual(typeof endpoints.resumeSwarm, 'function');
    assert.strictEqual(typeof endpoints.cancelSwarm, 'function');
    assert.strictEqual(typeof endpoints.synthesizeSwarm, 'function');
    assert.strictEqual(typeof endpoints.verifySwarm, 'function');
    assert.strictEqual(typeof endpoints.getSwarmAudit, 'function');
  });

  test('swarmApi wrapper exposes mapped methods', () => {
    assert.strictEqual(typeof swarmApi.create, 'function');
    assert.strictEqual(typeof swarmApi.list, 'function');
    assert.strictEqual(typeof swarmApi.get, 'function');
    assert.strictEqual(typeof swarmApi.getAgents, 'function');
    assert.strictEqual(typeof swarmApi.getTasks, 'function');
    assert.strictEqual(typeof swarmApi.getResults, 'function');
    assert.strictEqual(typeof swarmApi.getReviews, 'function');
    assert.strictEqual(typeof swarmApi.getDisagreements, 'function');
    assert.strictEqual(typeof swarmApi.getTimeline, 'function');
    assert.strictEqual(typeof swarmApi.pause, 'function');
    assert.strictEqual(typeof swarmApi.resume, 'function');
    assert.strictEqual(typeof swarmApi.cancel, 'function');
    assert.strictEqual(typeof swarmApi.synthesize, 'function');
    assert.strictEqual(typeof swarmApi.verify, 'function');
    assert.strictEqual(typeof swarmApi.getAudit, 'function');
  });
});

describe('SwarmView Component (Task 64)', () => {
  test('initializes with active_swarms tab and empty state collections', () => {
    const view = new SwarmView('mock-swarm-container');
    assert.strictEqual(view.activeTab, 'active_swarms');
    assert.strictEqual(view.sessions.length, 0);
    assert.strictEqual(view.agents.length, 0);
    assert.strictEqual(view.tasks.length, 0);
    assert.strictEqual(view.results.length, 0);
    assert.strictEqual(view.debates.length, 0);
    assert.strictEqual(view.disagreements.length, 0);
    assert.strictEqual(view.minorityReports.length, 0);
    assert.strictEqual(view.consensus, null);
    assert.strictEqual(view.auditTrail.length, 0);
    assert.strictEqual(view.isLoading, false);
  });

  test('switches tabs correctly across all swarm reasoning perspectives', () => {
    const view = new SwarmView('mock-swarm-container');
    const tabs = [
      'active_swarms',
      'agent_board',
      'reasoning',
      'debate',
      'disagreements',
      'consensus',
      'verification_audit'
    ];

    for (const tab of tabs) {
      view.setTab(tab);
      assert.strictEqual(view.activeTab, tab);
    }
  });

  test('selects session, agent, and disagreement models with full metadata', () => {
    const view = new SwarmView('mock-swarm-container');

    const mockSession = {
      session_id: 'swm_arch_eval_001',
      objective: {
        goal: 'Evaluate microservices vs modular monolith for low-latency ingest',
        risk_level: 'HIGH',
        priority: 1
      },
      topology: 'STAR',
      status: 'SYNTHESIZED',
      consensus_outcome: 'QUALIFIED_CONSENSUS',
      verification_status: 'VERIFIED'
    };
    view.selectSession(mockSession);
    assert.strictEqual(view.selectedSession.session_id, 'swm_arch_eval_001');
    assert.strictEqual(view.selectedSession.topology, 'STAR');

    const mockAgent = {
      agent_id: 'agent_sec_01',
      name: 'Sentinel-Security',
      role: 'SECURITY_ANALYST',
      health: 'HEALTHY',
      trust_level: 0.95,
      capabilities: ['threat_modeling', 'vulnerability_scanning'],
      limitations: ['cannot_execute_production_mutation']
    };
    view.selectAgent(mockAgent);
    assert.strictEqual(view.selectedAgent.agent_id, 'agent_sec_01');
    assert.strictEqual(view.selectedAgent.role, 'SECURITY_ANALYST');

    const mockDisagreement = {
      disagreement_id: 'disag_latency_tradeoff_01',
      disagreement_type: 'CAUSAL',
      issue: 'Microservice network hops add 4ms P99 latency vs Monolith memory bus',
      participating_agents: ['agent_arch_01', 'agent_perf_02'],
      status: 'RESOLVED_BY_DEBATE'
    };
    view.selectDisagreement(mockDisagreement);
    assert.strictEqual(view.selectedDisagreement.disagreement_id, 'disag_latency_tradeoff_01');
    assert.strictEqual(view.selectedDisagreement.disagreement_type, 'CAUSAL');
  });

  test('renders consensus and preserves minority reports without loss', () => {
    const view = new SwarmView('mock-swarm-container');
    const mockConsensus = {
      outcome: 'QUALIFIED_CONSENSUS',
      confidence: 0.88,
      verified: true,
      majority_view: 'Deploy modular monolith with asynchronous replication for ingest stage.',
      minority_reports: [
        {
          agent_id: 'agent_critic_09',
          dissenting_claim: 'Scaling monolith will cause blast radius expansion under network partition.',
          failure_scenario: 'Split-brain database lock failure during network partition',
          evidence_citations: ['ev_bench_stress_partition_01']
        }
      ]
    };

    view.consensus = mockConsensus;
    view.minorityReports = mockConsensus.minority_reports;

    assert.strictEqual(view.consensus.outcome, 'QUALIFIED_CONSENSUS');
    assert.strictEqual(view.minorityReports.length, 1);
    assert.strictEqual(view.minorityReports[0].agent_id, 'agent_critic_09');
    assert.ok(view.minorityReports[0].failure_scenario.includes('Split-brain'));
  });
});
