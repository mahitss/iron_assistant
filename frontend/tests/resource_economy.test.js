/**
 * Unit tests for Kairo Autonomous Resource Economy, Capability Allocation & Cognitive Budget Engine (Task 77).
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { resourceEconomyApi, nativeRuntimeApi, nativeNetworkApi, reliabilityApi, recoverySimulationApi, reliabilityIntelligenceApi, capabilityLifecycleApi } from '../lib/api/endpoints.js';
import { ResourceCenterView } from '../components/orchestration/resourceCenterView.js';

describe('Autonomous Resource Economy & Cognitive Budget API (Task 77)', () => {
  test('resourceEconomyApi exposes all authoritative endpoints', () => {
    assert.strictEqual(typeof resourceEconomyApi.getOverview, 'function');
    assert.strictEqual(typeof resourceEconomyApi.estimateDemand, 'function');
    assert.strictEqual(typeof resourceEconomyApi.createBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.listBudgets, 'function');
    assert.strictEqual(typeof resourceEconomyApi.getBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.checkBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.allocateBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.resetBudget, 'function');
    assert.strictEqual(typeof resourceEconomyApi.requestPreemption, 'function');
    assert.strictEqual(typeof resourceEconomyApi.checkpointTask, 'function');
    assert.strictEqual(typeof resourceEconomyApi.resumeTask, 'function');
    assert.strictEqual(typeof resourceEconomyApi.listPreemptions, 'function');
    assert.strictEqual(typeof resourceEconomyApi.detectDeadlocks, 'function');
    assert.strictEqual(typeof resourceEconomyApi.resolveDeadlocks, 'function');
    assert.strictEqual(typeof resourceEconomyApi.getFairnessMetrics, 'function');
    assert.strictEqual(typeof resourceEconomyApi.evaluateTradeOff, 'function');
    assert.strictEqual(typeof resourceEconomyApi.routeModel, 'function');
  });
});

describe('ResourceCenterView Component (Task 77)', () => {
  test('initializes with overview subtab and default collections', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);
    assert.strictEqual(view.activeSubTab, 'overview');
    assert.strictEqual(view.budgetsData.length, 0);
    assert.strictEqual(view.preemptionsData.length, 0);
    assert.strictEqual(view.deadlocksData.length, 0);
  });

  test('switches subtabs correctly across all 6 views', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    view.setSubTab('budgets');
    assert.strictEqual(view.activeSubTab, 'budgets');

    view.setSubTab('preemption');
    assert.strictEqual(view.activeSubTab, 'preemption');

    view.setSubTab('deadlock');
    assert.strictEqual(view.activeSubTab, 'deadlock');

    view.setSubTab('tradeoffs');
    assert.strictEqual(view.activeSubTab, 'tradeoffs');

    view.setSubTab('fairness');
    assert.strictEqual(view.activeSubTab, 'fairness');

    view.setSubTab('overview');
    assert.strictEqual(view.activeSubTab, 'overview');
  });

  test('enforces explicit safety badge formatting', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    const availableBadge = view.formatSafetyBadge('AVAILABLE');
    assert.match(availableBadge, /AVAILABLE/);
    assert.match(availableBadge, /#10b981/);

    const reservedBadge = view.formatSafetyBadge('RESERVED');
    assert.match(reservedBadge, /RESERVED/);
    assert.match(reservedBadge, /#f59e0b/);

    const allocatedBadge = view.formatSafetyBadge('ALLOCATED');
    assert.match(allocatedBadge, /ALLOCATED/);
    assert.match(allocatedBadge, /#3b82f6/);

    const degradedBadge = view.formatSafetyBadge('DEGRADED');
    assert.match(degradedBadge, /DEGRADED/);
    assert.match(degradedBadge, /#ea580c/);

    const exhaustedBadge = view.formatSafetyBadge('EXHAUSTED');
    assert.match(exhaustedBadge, /EXHAUSTED/);
    assert.match(exhaustedBadge, /#ef4444/);
  });

  test('renders base HTML structure and sub-navigation cleanly', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.render();

    assert.match(htmlOutput, /Autonomous Resource Economy & Cognitive Budget Center/);
    assert.match(htmlOutput, /1\. Economy Overview/);
    assert.match(htmlOutput, /2\. Cognitive Budgets/);
    assert.match(htmlOutput, /3\. Preemption & Queue/);
    assert.match(htmlOutput, /4\. Deadlock & Contention/);
    assert.match(htmlOutput, /5\. Trade-Offs & Degradation/);
    assert.match(htmlOutput, /6\. Starvation & Fair Share/);
    assert.match(htmlOutput, /7\. Native Enforcement/);
    assert.match(htmlOutput, /8\. Native Tool Fabric/);
    assert.match(htmlOutput, /9\. Computer Substrate/);
  });

  test('switches to native enforcement subtab and renders matrix and explanation', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.setSubTab('native');

    assert.strictEqual(view.activeSubTab, 'native');
    assert.match(htmlOutput, /Cross-Platform Native Enforcement Matrix/);
    assert.match(htmlOutput, /Execution Resource Lifecycle & Explanation/);
    assert.match(htmlOutput, /RUST NATIVE/);
  });

  test('switches to native tool fabric subtab and renders tool catalog and invariants', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.nativeToolsData = [
      {
        name: 'native_hash',
        version: '1.0.0',
        execution_class: 'NATIVE_RUST',
        preference: 'NATIVE_PREFERRED',
        capability_id: 'sandbox.hash',
        sandbox_profile: 'STANDARD',
        permission_level: 'READ',
        availability: 'AVAILABLE',
        metrics: { invocations: 12, success_rate: 1.0, avg_latency_ms: 4.2, fallbacks: 0 },
      },
    ];
    view.setSubTab('tools');

    assert.strictEqual(view.activeSubTab, 'tools');
    assert.match(htmlOutput, /Native Tool Execution Fabric Catalog/);
    assert.match(htmlOutput, /Runtime Substrate State/);
    assert.match(htmlOutput, /Registered Native Tools/);
    assert.match(htmlOutput, /Zero Shell Strings/);
    assert.match(htmlOutput, /native_hash/);
    assert.match(htmlOutput, /sandbox\.hash/);
  });

  test('switches to computer substrate subtab and renders window/process/display tables and safety alerts', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.nativeWindowsData = [
      {
        window_id: 65538,
        title: 'Visual Studio Code',
        process_name: 'Code.exe',
        pid: 12345,
        rect: { x: 0, y: 0, width: 1920, height: 1080 },
        is_visible: true,
        is_focused: true,
      },
    ];
    view.nativeDisplaysData = [
      {
        display_id: 0,
        name: 'Primary Display',
        width: 1920,
        height: 1080,
        scale_factor: 1.0,
        is_primary: true,
      },
    ];
    view.setSubTab('computer');

    assert.strictEqual(view.activeSubTab, 'computer');
    assert.match(htmlOutput, /Observed Windows/);
    assert.match(htmlOutput, /Target Context Verification & Safety Invariants/);
    assert.match(htmlOutput, /ABORT_TARGET_CHANGED/);
    assert.match(htmlOutput, /Visual Studio Code/);
    assert.match(htmlOutput, /Code\.exe/);
    assert.match(htmlOutput, /FOCUSED/);
    assert.match(htmlOutput, /Connected Displays/);
  });

  test('switches to subtab 10 (Network Fabric) and renders live telemetry and invariants', () => {
    let htmlOutput = '';
    const mockContainer = {
      set innerHTML(val) { htmlOutput = val; },
      get innerHTML() { return htmlOutput; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };
    const view = new ResourceCenterView(mockContainer);
    view.nativeNetworkHealth = {
      state: 'HEALTHY',
      active_requests: 3,
      active_connections: 5,
      idle_connections: 2,
      total_requests_executed: 42,
      total_errors: 0,
      circuit_breaker_open: false,
      circuit_breaker_state: 'CLOSED',
      circuit_breaker_failures: 0,
      ssrf_blocks_total: 7,
      concurrency_limit: 64,
      concurrency_permits_available: 61,
    };
    view.setSubTab('network');

    assert.strictEqual(view.activeSubTab, 'network');
    assert.match(htmlOutput, /Fabric Status/);
    assert.match(htmlOutput, /SSRF Blocks Defended/);
    assert.match(htmlOutput, /Zero-Trust Rust Daemon Substrate/);
    assert.match(htmlOutput, /Pre-Validated Socket Resolution/);
    assert.match(htmlOutput, /Zero Remote Content Ingestion as Prompt/);
    assert.match(htmlOutput, /EmergencyStop Authority/);
    assert.match(htmlOutput, /native\.net\.resolve/);
    assert.match(htmlOutput, /native_dns_resolve/);
    assert.match(htmlOutput, /native\.net\.fetch/);
    assert.match(htmlOutput, /native_http_fetch/);
    assert.match(htmlOutput, /native\.net\.request/);
    assert.match(htmlOutput, /native_http_request/);
    assert.match(htmlOutput, /Circuit Breaker/);
    assert.match(htmlOutput, /CLOSED/);
  });
});

describe('Native Tool Execution Fabric API (Task 83)', () => {
  test('nativeRuntimeApi exposes all Task 83 tool fabric methods', () => {
    assert.strictEqual(typeof nativeRuntimeApi.listTools, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.getToolHealth, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.getToolDetail, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.executeTool, 'function');
  });
});

describe('Native Computer Interaction Substrate API (Task 84)', () => {
  test('nativeRuntimeApi exposes all Task 84 computer interaction methods', () => {
    assert.strictEqual(typeof nativeRuntimeApi.listWindows, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.listProcesses, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.listDisplays, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.captureScreen, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.readClipboard, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.writeClipboard, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.executeMouse, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.executeKeyboard, 'function');
  });
});

describe('Native Network Execution & Connection Fabric API (Task 85)', () => {
  test('nativeRuntimeApi and nativeNetworkApi expose all Task 85 network methods', () => {
    assert.strictEqual(typeof nativeRuntimeApi.resolveDns, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.httpFetch, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.httpRequest, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.getNetworkHealth, 'function');

    assert.strictEqual(typeof nativeNetworkApi.resolveDns, 'function');
    assert.strictEqual(typeof nativeNetworkApi.httpFetch, 'function');
    assert.strictEqual(typeof nativeNetworkApi.httpRequest, 'function');
    assert.strictEqual(typeof nativeNetworkApi.getNetworkHealth, 'function');
  });
});

describe('Native Protocol Hardening & Distributed Execution Contract (Task 87)', () => {
  test('nativeRuntimeApi exposes all Task 87 contract methods', () => {
    assert.strictEqual(typeof nativeRuntimeApi.getProtocolContractStatus, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.emergencyStop, 'function');
    assert.strictEqual(typeof nativeRuntimeApi.reconcileOrphans, 'function');
  });

  test('ResourceCenterView switches to Protocol Contract subtab and renders invariants', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    view.setSubTab('contract');
    assert.strictEqual(view.activeSubTab, 'contract');

    const htmlOutput = view.renderProtocolContractTab();
    assert.match(htmlOutput, /Native Runtime Protocol & Distributed Execution Contract/);
    assert.match(htmlOutput, /Session Binding/);
    assert.match(htmlOutput, /Capability Attestation/);
    assert.match(htmlOutput, /At-Most-Once Side Effects/);
    assert.match(htmlOutput, /ReplayGuard LRU Window/);
    assert.match(htmlOutput, /Anti-TOCTOU Revalidation/);
    assert.match(htmlOutput, /Emergency Stop Priority/);
    assert.match(htmlOutput, /UNKNOWN_OUTCOME/);
    assert.match(htmlOutput, /btn-reconcile-orphans/);
    assert.match(htmlOutput, /btn-protocol-emergency-stop/);
  });
});

describe('Autonomous Runtime Reliability & Self-Healing (Task 88)', () => {
  test('reliabilityApi exposes all Task 88 reliability endpoints', () => {
    assert.strictEqual(typeof reliabilityApi.getHealth, 'function');
    assert.strictEqual(typeof reliabilityApi.getIncidents, 'function');
    assert.strictEqual(typeof reliabilityApi.getIncidentDetails, 'function');
    assert.strictEqual(typeof reliabilityApi.recoverIncident, 'function');
    assert.strictEqual(typeof reliabilityApi.getFailures, 'function');
    assert.strictEqual(typeof reliabilityApi.getRecoveryList, 'function');
    assert.strictEqual(typeof reliabilityApi.getRecoveryDetails, 'function');
    assert.strictEqual(typeof reliabilityApi.approveRecovery, 'function');
    assert.strictEqual(typeof reliabilityApi.getComponentsMatrix, 'function');
    assert.strictEqual(typeof reliabilityApi.triggerFault, 'function');
  });

  test('ResourceCenterView switches to Reliability subtab and renders self-healing components', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    view.setSubTab('reliability');
    assert.strictEqual(view.activeSubTab, 'reliability');

    const htmlOutput = view.renderReliabilityTab();
    assert.match(htmlOutput, /Subsystem Reliability/);
    assert.match(htmlOutput, /Open Incidents/);
    assert.match(htmlOutput, /Crash Loop Circuit Breakers/);
    assert.match(htmlOutput, /Chaos & Fault Injection/);
    assert.match(htmlOutput, /Deterministic Self-Healing Invariants/);
    assert.match(htmlOutput, /Emergency Stop Absolute Priority/);
    assert.match(htmlOutput, /Non-LLM Verification/);
    assert.match(htmlOutput, /Crash Loop Circuit Breaker/);
    assert.match(htmlOutput, /Resource Economy Budgeting/);
    assert.match(htmlOutput, /Stability Window Monitoring/);
  });
});

describe('Autonomous Recovery Simulation, Digital Twin & Resilience Validation (Task 89)', () => {
  test('recoverySimulationApi exposes all Task 89 simulation endpoints', () => {
    assert.strictEqual(typeof recoverySimulationApi.captureSnapshot, 'function');
    assert.strictEqual(typeof recoverySimulationApi.getLatestSnapshot, 'function');
    assert.strictEqual(typeof recoverySimulationApi.getSnapshot, 'function');
    assert.strictEqual(typeof recoverySimulationApi.runSimulation, 'function');
    assert.strictEqual(typeof recoverySimulationApi.listSimulations, 'function');
    assert.strictEqual(typeof recoverySimulationApi.getSimulation, 'function');
    assert.strictEqual(typeof recoverySimulationApi.listChaosScenarios, 'function');
    assert.strictEqual(typeof recoverySimulationApi.runChaosDrill, 'function');
    assert.strictEqual(typeof recoverySimulationApi.calibrateRecovery, 'function');
    assert.strictEqual(typeof recoverySimulationApi.getScorecards, 'function');
    assert.strictEqual(typeof recoverySimulationApi.getBenchmarks, 'function');
    assert.strictEqual(typeof recoverySimulationApi.getRegressions, 'function');
    assert.strictEqual(typeof recoverySimulationApi.getComparisons, 'function');
  });

  test('ResourceCenterView switches to Simulation subtab and renders digital twin and chaos drills', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    view.setSubTab('simulation');
    assert.strictEqual(view.activeSubTab, 'simulation');

    const htmlOutput = view.renderSimulationTab();
    assert.match(htmlOutput, /Autonomous Recovery Simulation & Digital Twin/);
    assert.match(htmlOutput, /Operational Digital Twin Snapshot/);
    assert.match(htmlOutput, /Pre-Recovery Consequence Simulation/);
    assert.match(htmlOutput, /Chaos Resilience Drill Library/);
    assert.match(htmlOutput, /Strategy Scorecards & Regression Tracking/);
    assert.match(htmlOutput, /Resilience Benchmark Dimensions/);
    assert.match(htmlOutput, /Deterministic Simulation Firewall Invariants/);
    assert.match(htmlOutput, /SIMULATION_ONLY/);
    assert.match(htmlOutput, /btn-capture-snapshot/);
    assert.match(htmlOutput, /btn-run-simulation/);
  });
});

describe('Autonomous Reliability Intelligence & Predictive Failure Prevention (Task 90)', () => {
  test('reliabilityIntelligenceApi exposes all Task 90 endpoints', () => {
    assert.strictEqual(typeof reliabilityIntelligenceApi.getSignals, 'function');
    assert.strictEqual(typeof reliabilityIntelligenceApi.getIncidents, 'function');
    assert.strictEqual(typeof reliabilityIntelligenceApi.getIncidentDetails, 'function');
    assert.strictEqual(typeof reliabilityIntelligenceApi.getCandidateDetails, 'function');
    assert.strictEqual(typeof reliabilityIntelligenceApi.getScorecards, 'function');
    assert.strictEqual(typeof reliabilityIntelligenceApi.getCalibration, 'function');
    assert.strictEqual(typeof reliabilityIntelligenceApi.evaluateTelemetry, 'function');
  });

  test('ResourceCenterView switches to Intelligence subtab and renders predictive prevention view', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    view.setSubTab('intelligence');
    assert.strictEqual(view.activeSubTab, 'intelligence');

    const htmlOutput = view.renderReliabilityIntelligenceTab();
    assert.match(htmlOutput, /Autonomous Reliability Intelligence & Predictive Failure Prevention/);
    assert.match(htmlOutput, /Active Precursor Signals/);
    assert.match(htmlOutput, /Predictive Incidents & Decision Explanations/);
    assert.match(htmlOutput, /Prevention Strategy Effectiveness Scorecards/);
    assert.match(htmlOutput, /Autonomous Prevention Invariant/);
    assert.match(htmlOutput, /btn-evaluate-telemetry/);
  });
});

describe('Autonomous Capability Lifecycle, Versioning & Evolution Engine (Task 91)', () => {
  test('capabilityLifecycleApi exposes all Task 91 endpoints', () => {
    assert.strictEqual(typeof capabilityLifecycleApi.listCapabilities, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.getCapability, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.getVersions, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.getHealth, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.getDependencies, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.getLifecycle, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.discoverCapability, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.validateCapability, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.testConformance, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.simulateRollout, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.startCanary, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.promoteCapability, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.rollbackCapability, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.deprecateCapability, 'function');
    assert.strictEqual(typeof capabilityLifecycleApi.retireCapability, 'function');
  });

  test('ResourceCenterView switches to Capabilities subtab and renders evolution view', () => {
    const mockContainer = { innerHTML: '', querySelector: () => null, querySelectorAll: () => [] };
    const view = new ResourceCenterView(mockContainer);

    view.setSubTab('capabilities');
    assert.strictEqual(view.activeSubTab, 'capabilities');

    const htmlOutput = view.renderCapabilitiesTab();
    assert.match(htmlOutput, /Autonomous Capability Lifecycle, Versioning & Safe Evolution Engine/);
    assert.match(htmlOutput, /AUTONOMOUS EVOLUTION ≠ AUTONOMOUS AUTHORIZATION/);
    assert.match(htmlOutput, /Capability Catalog & Version Lineage/);
    assert.match(htmlOutput, /11 Mandatory Safety Promotion Gates/);
    assert.match(htmlOutput, /btn-discover-sample-capability/);
  });
});




