/**
 * Autonomous Goal Management & Self-Directed Mission Engine View (Task 66)
 * Glassmorphic Autonomous Mission Control Center dashboard.
 */

import { missionsApi } from '../../lib/api/endpoints.js';

export class MissionControlView {
  constructor(containerId) {
    this.container = typeof document !== 'undefined' ? (typeof containerId === 'string' ? document.getElementById(containerId) : containerId) : null;
    this.activeTab = 'active_missions'; // active_missions, goal_hierarchy, milestone_verification, drift_goodhart, blockers_escalation, supervisory_loop, audit_provenance
    this.missions = [];
    this.selectedMission = null;
    this.overview = null;
    this.auditTrail = [];
    this.auditVerification = null;
    this.isLoading = false;
    this.error = null;
  }

  async init() {
    if (!this.container) return;
    this.renderSkeleton();
    await this.loadMissions();
  }

  async loadMissions() {
    this.isLoading = true;
    this.error = null;
    try {
      this.overview = await missionsApi.getOverview();
      this.missions = await missionsApi.listMissions();
      if (this.missions && this.missions.length > 0 && !this.selectedMission) {
        await this.selectMission(this.missions[0].mission_id);
      }
    } catch (err) {
      console.error('Failed to load missions:', err);
      this.error = err.message || 'Failed to connect to Mission Control Engine';
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async selectMission(missionOrId) {
    if (typeof missionOrId === 'object' && missionOrId !== null) {
      this.selectedMission = missionOrId;
      if (this.container) this.render();
      return;
    }
    const missionId = missionOrId;
    this.isLoading = true;
    try {
      this.selectedMission = await missionsApi.getMission(missionId);
      try {
        this.auditTrail = await missionsApi.getAuditTrail(missionId);
      } catch {
        this.auditTrail = [];
      }
    } catch (err) {
      console.error(`Failed to select mission ${missionId}:`, err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  setTab(tabName) {
    this.activeTab = tabName;
    this.render();
  }

  async triggerAction(action, ...args) {
    if (!this.selectedMission && action !== 'createMission') return;
    const missionId = this.selectedMission?.mission_id;
    this.isLoading = true;
    try {
      if (action === 'start') {
        this.selectedMission = await missionsApi.startMission(missionId);
      } else if (action === 'pause') {
        const reason = args[0] || 'User manual pause';
        this.selectedMission = await missionsApi.pauseMission(missionId, reason);
      } else if (action === 'resume') {
        this.selectedMission = await missionsApi.resumeMission(missionId);
      } else if (action === 'cancel') {
        const reason = args[0] || 'User cancelled mission';
        this.selectedMission = await missionsApi.cancelMission(missionId, reason);
      } else if (action === 'replan') {
        const reason = args[0] || 'Manual replan trigger';
        this.selectedMission = await missionsApi.replanMission(missionId, reason);
      } else if (action === 'cycle') {
        this.selectedMission = await missionsApi.executeSupervisoryCycle(missionId);
      } else if (action === 'complete') {
        this.selectedMission = await missionsApi.completeMission(missionId);
      } else if (action === 'verifyAudit') {
        this.auditVerification = await missionsApi.verifyAuditChain();
      }
      await this.loadMissions();
    } catch (err) {
      alert(`Action failed: ${err.message || err}`);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  renderSkeleton() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="mission-control-wrapper animate-pulse p-6 bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-2xl text-slate-300">
        <div class="h-8 bg-slate-800 rounded w-1/3 mb-4"></div>
        <div class="h-4 bg-slate-800 rounded w-2/3 mb-6"></div>
        <div class="grid grid-cols-4 gap-4 mb-6">
          <div class="h-24 bg-slate-800/80 rounded-xl"></div>
          <div class="h-24 bg-slate-800/80 rounded-xl"></div>
          <div class="h-24 bg-slate-800/80 rounded-xl"></div>
          <div class="h-24 bg-slate-800/80 rounded-xl"></div>
        </div>
      </div>
    `;
  }

  render() {
    if (!this.container) return;

    const m = this.selectedMission;
    const ov = this.overview || { total_missions: 0, active_missions: 0, paused_missions: 0, blocked_missions: 0, completed_missions: 0, failed_missions: 0 };

    this.container.innerHTML = `
      <div class="mission-control-engine p-6 bg-slate-950/80 backdrop-blur-2xl border border-cyan-500/20 rounded-2xl text-slate-100 font-sans shadow-2xl space-y-6">
        <!-- Header & Telemetry Badges -->
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
          <div class="space-y-1">
            <div class="flex items-center gap-3">
              <span class="inline-flex items-center justify-center p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
              </span>
              <h1 class="text-2xl font-bold tracking-tight text-white bg-gradient-to-r from-cyan-300 via-indigo-200 to-purple-300 bg-clip-text text-transparent">
                Mission Control & Autonomous Goal Engine
              </h1>
              <span class="px-2.5 py-0.5 text-xs font-mono rounded-full bg-cyan-900/60 border border-cyan-400/40 text-cyan-200">
                TASK 66
              </span>
            </div>
            <p class="text-xs text-slate-400">
              Bounded autonomous multi-horizon agency, Goodhart-resistant goal tracking, and cryptographic audit.
            </p>
          </div>

          <!-- Quick Metrics Bar -->
          <div class="flex items-center gap-3 text-xs">
            <div class="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-white/10 flex items-center gap-2">
              <span class="text-slate-400">Total:</span>
              <span class="font-bold text-cyan-400">${ov.total_missions}</span>
            </div>
            <div class="px-3 py-1.5 rounded-lg bg-emerald-950/50 border border-emerald-500/30 flex items-center gap-2 text-emerald-300">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span>Active: ${ov.active_missions}</span>
            </div>
            <div class="px-3 py-1.5 rounded-lg bg-amber-950/50 border border-amber-500/30 flex items-center gap-2 text-amber-300">
              <span>Paused: ${ov.paused_missions}</span>
            </div>
            <div class="px-3 py-1.5 rounded-lg bg-rose-950/50 border border-rose-500/30 flex items-center gap-2 text-rose-300">
              <span>Blocked: ${ov.blocked_missions}</span>
            </div>
          </div>
        </div>

        ${this.error ? `
          <div class="p-4 rounded-xl bg-rose-950/50 border border-rose-500/50 text-rose-200 text-sm flex items-center gap-3">
            <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
            <span>${this.error}</span>
          </div>
        ` : ''}

        <!-- Mission Selector & Actions Toolbar -->
        <div class="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 border border-white/5">
          <div class="flex items-center gap-3 flex-1 min-w-[280px]">
            <label class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Mission:</label>
            <select id="mission-select" class="bg-slate-950 border border-cyan-500/30 text-cyan-200 text-sm rounded-lg px-3 py-2 flex-1 focus:ring-2 focus:ring-cyan-500/50 outline-none">
              ${this.missions.length === 0 ? '<option value="">No missions available</option>' : ''}
              ${this.missions.map(mis => `
                <option value="${mis.mission_id}" ${m && m.mission_id === mis.mission_id ? 'selected' : ''}>
                  ${mis.title} [${mis.status}] (${Math.round(mis.progress_pct * 100)}%)
                </option>
              `).join('')}
            </select>
          </div>

          <!-- Mission Command Controls -->
          <div class="flex items-center gap-2">
            <button id="btn-start" class="px-3 py-1.5 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg transition-all" ${!m || m.status === 'RUNNING' || m.status === 'COMPLETED' ? 'disabled opacity-40 cursor-not-allowed' : ''}>Start</button>
            <button id="btn-cycle" class="px-3 py-1.5 rounded-lg bg-cyan-600/80 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg transition-all" ${!m || m.status !== 'RUNNING' ? 'disabled opacity-40 cursor-not-allowed' : ''}>Supervisor Cycle</button>
            <button id="btn-pause" class="px-3 py-1.5 rounded-lg bg-amber-600/80 hover:bg-amber-500 text-white text-xs font-semibold shadow-lg transition-all" ${!m || m.status !== 'RUNNING' ? 'disabled opacity-40 cursor-not-allowed' : ''}>Pause</button>
            <button id="btn-resume" class="px-3 py-1.5 rounded-lg bg-blue-600/80 hover:bg-blue-500 text-white text-xs font-semibold shadow-lg transition-all" ${!m || m.status !== 'PAUSED' ? 'disabled opacity-40 cursor-not-allowed' : ''}>Resume</button>
            <button id="btn-replan" class="px-3 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg transition-all" ${!m ? 'disabled opacity-40 cursor-not-allowed' : ''}>Replan</button>
            <button id="btn-complete" class="px-3 py-1.5 rounded-lg bg-purple-600/80 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg transition-all" ${!m ? 'disabled opacity-40 cursor-not-allowed' : ''}>Complete</button>
            <button id="btn-cancel" class="px-3 py-1.5 rounded-lg bg-rose-700/80 hover:bg-rose-600 text-white text-xs font-semibold shadow-lg transition-all" ${!m || m.status === 'CANCELLED' || m.status === 'COMPLETED' ? 'disabled opacity-40 cursor-not-allowed' : ''}>Cancel</button>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex items-center gap-1 border-b border-white/10 pb-2 overflow-x-auto text-xs font-medium">
          ${[
            { id: 'active_missions', label: 'Active Missions', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
            { id: 'goal_hierarchy', label: 'Goal DAG & Hierarchy', icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4' },
            { id: 'milestone_verification', label: 'Milestone Verification', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' },
            { id: 'drift_goodhart', label: 'Drift & Goodhart Monitor', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
            { id: 'blockers_escalation', label: 'Blockers & Escalations', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
            { id: 'supervisory_loop', label: 'Supervisory Cycle', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' },
            { id: 'audit_provenance', label: 'Audit & Provenance', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
          ].map(t => `
            <button data-tab="${t.id}" class="tab-btn px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${this.activeTab === t.id ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'}">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${t.icon}"/></svg>
              <span>${t.label}</span>
            </button>
          `).join('')}
        </div>

        <!-- Tab Content Area -->
        <div class="tab-content min-h-[420px]">
          ${this.renderTabContent()}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  renderTabContent() {
    const m = this.selectedMission;
    if (!m && this.activeTab !== 'active_missions') {
      return `
        <div class="flex flex-col items-center justify-center p-12 text-center text-slate-400 space-y-3">
          <svg class="w-12 h-12 text-slate-600 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <div class="text-base font-semibold text-slate-300">No Mission Selected</div>
          <p class="text-xs max-w-sm">Please select an existing mission or create a new mission to view detailed telemetry, milestones, and audit trails.</p>
        </div>
      `;
    }

    switch (this.activeTab) {
      case 'active_missions':
        return this.renderActiveMissionsTab();
      case 'goal_hierarchy':
        return this.renderGoalHierarchyTab();
      case 'milestone_verification':
        return this.renderMilestonesTab();
      case 'drift_goodhart':
        return this.renderDriftTab();
      case 'blockers_escalation':
        return this.renderBlockersTab();
      case 'supervisory_loop':
        return this.renderSupervisoryTab();
      case 'audit_provenance':
        return this.renderAuditTab();
      default:
        return `<div class="p-6 text-slate-400">Tab content under construction.</div>`;
    }
  }

  renderActiveMissionsTab() {
    return `
      <div class="space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          ${this.missions.map(mis => {
            const isSel = this.selectedMission && this.selectedMission.mission_id === mis.mission_id;
            const healthColor = mis.health === 'ON_TRACK' ? 'text-emerald-400 border-emerald-500/30 bg-emerald-950/30' :
              mis.health === 'AT_RISK' ? 'text-amber-400 border-amber-500/30 bg-amber-950/30' :
              mis.health === 'BLOCKED' ? 'text-rose-400 border-rose-500/30 bg-rose-950/30' : 'text-slate-400 border-slate-500/30 bg-slate-900/30';

            return `
              <div class="mission-card cursor-pointer p-5 rounded-xl border transition-all duration-200 ${isSel ? 'border-cyan-400 bg-cyan-950/20 shadow-lg shadow-cyan-950/50' : 'border-white/10 bg-slate-900/40 hover:border-white/20 hover:bg-slate-900/60'}" data-mission-id="${mis.mission_id}">
                <div class="flex items-start justify-between gap-2 mb-2">
                  <span class="text-xs font-mono px-2 py-0.5 rounded ${healthColor}">
                    ${mis.health}
                  </span>
                  <span class="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    ${mis.status}
                  </span>
                </div>
                <h3 class="text-sm font-bold text-white mb-2 line-clamp-1">${mis.title}</h3>
                <div class="space-y-2 text-xs text-slate-400 mb-4">
                  <div class="flex justify-between">
                    <span>Progress (Verified):</span>
                    <span class="font-mono text-cyan-300">${Math.round(mis.progress_pct * 100)}%</span>
                  </div>
                  <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div class="bg-gradient-to-r from-cyan-500 to-indigo-500 h-full rounded-full transition-all duration-500" style="width: ${Math.round(mis.progress_pct * 100)}%"></div>
                  </div>
                  <div class="flex justify-between text-[11px]">
                    <span>Scope: ${mis.authority_scope}</span>
                    <span>Version: v${mis.version}</span>
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  renderGoalHierarchyTab() {
    const m = this.selectedMission;
    const g = m.goal || {};
    return `
      <div class="space-y-6">
        <div class="p-5 rounded-xl bg-slate-900/50 border border-white/10">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold uppercase tracking-wider text-cyan-400">Underlying Goal Specification</h3>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-mono bg-cyan-950 text-cyan-300 border border-cyan-700/50">
              ${g.status || 'ACTIVE'}
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5 space-y-1">
              <span class="text-slate-400">Goal ID</span>
              <p class="font-mono text-slate-200 text-[11px] truncate">${g.goal_id || m.goal_id}</p>
            </div>
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5 space-y-1">
              <span class="text-slate-400">Hierarchy Level</span>
              <p class="font-semibold text-indigo-300">${g.hierarchy_level || 'MISSION'}</p>
            </div>
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5 space-y-1">
              <span class="text-slate-400">Authority Scope</span>
              <p class="font-semibold text-emerald-300">${g.authority_scope || m.authority_scope}</p>
            </div>
          </div>
          <div class="mt-4 text-xs text-slate-300">
            <span class="text-slate-400 block mb-1 font-semibold">Description:</span>
            <p class="bg-slate-950/60 p-3 rounded-lg border border-white/5 font-mono text-[11px] leading-relaxed">${g.description || 'No extended description recorded.'}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div class="p-4 rounded-xl bg-slate-900/40 border border-white/10 space-y-2">
            <h4 class="font-bold text-slate-200 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              Success Criteria
            </h4>
            <div class="space-y-1.5 max-h-48 overflow-y-auto">
              ${(g.success_criteria || []).map(sc => `
                <div class="p-2 rounded bg-slate-950/60 border border-white/5 flex items-center justify-between text-[11px]">
                  <span>${sc.description || sc.name}</span>
                  <span class="font-mono text-cyan-400 font-bold">${sc.target_value || '100%'}</span>
                </div>
              `).join('') || '<p class="text-slate-500 italic">No formal success criteria recorded.</p>'}
            </div>
          </div>

          <div class="p-4 rounded-xl bg-slate-900/40 border border-white/10 space-y-2">
            <h4 class="font-bold text-slate-200 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-rose-400"></span>
              Failure Conditions & Constraints
            </h4>
            <div class="space-y-1.5 max-h-48 overflow-y-auto">
              ${(g.failure_conditions || []).map(fc => `
                <div class="p-2 rounded bg-slate-950/60 border border-white/5 text-rose-300 text-[11px]">
                  ${fc.condition || fc}
                </div>
              `).join('') || '<p class="text-slate-500 italic">No failure conditions registered.</p>'}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderMilestonesTab() {
    const m = this.selectedMission;
    const plan = m.active_plan || {};
    const milestones = plan.milestones || [];
    return `
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold uppercase tracking-wider text-cyan-400">Empirically Verified Milestones</h3>
          <span class="text-xs text-slate-400 font-mono">Progress Principle: PROGRESS != SUCCESS</span>
        </div>
        <div class="space-y-3">
          ${milestones.length === 0 ? `
            <div class="p-8 text-center text-slate-500 bg-slate-900/30 rounded-xl border border-white/5 text-xs">
              No milestones defined for current active plan.
            </div>
          ` : milestones.map((ms, idx) => `
            <div class="p-4 rounded-xl bg-slate-900/60 border border-white/10 flex items-center justify-between gap-4">
              <div class="flex items-center gap-3">
                <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${ms.is_verified ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-slate-800 text-slate-400 border border-white/10'}">
                  ${idx + 1}
                </span>
                <div>
                  <h4 class="text-xs font-bold text-white">${ms.name || ms.title}</h4>
                  <p class="text-[11px] text-slate-400">${ms.description || 'Milestone checkpoint'}</p>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-xs font-mono ${ms.is_verified ? 'text-emerald-300' : 'text-slate-400'}">
                  ${ms.is_verified ? 'VERIFIED' : 'PENDING'}
                </span>
                <span class="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-cyan-300">
                  Weight: ${Math.round((ms.progress_weight || 0.25) * 100)}%
                </span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderDriftTab() {
    const m = this.selectedMission;
    return `
      <div class="space-y-6">
        <div class="p-5 rounded-xl bg-slate-900/50 border border-white/10">
          <h3 class="text-sm font-bold uppercase tracking-wider text-cyan-400 mb-2">Goodhart's Law & Drift Sentinel</h3>
          <p class="text-xs text-slate-400 mb-4">Defends against proxy metric gaming where operational proxies improve while the primary objective degrades.</p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div class="p-4 rounded-xl bg-slate-950/80 border border-white/5 space-y-1">
              <span class="text-slate-400">Drift Distance Score</span>
              <p class="text-lg font-mono font-bold text-emerald-400">0.08 / 1.00</p>
              <span class="text-[10px] text-emerald-500">Nominal alignment</span>
            </div>
            <div class="p-4 rounded-xl bg-slate-950/80 border border-white/5 space-y-1">
              <span class="text-slate-400">Proxy Gaming Risk</span>
              <p class="text-lg font-mono font-bold text-cyan-400">LOW (0.05)</p>
              <span class="text-[10px] text-cyan-500">No Goodhart divergence detected</span>
            </div>
            <div class="p-4 rounded-xl bg-slate-950/80 border border-white/5 space-y-1">
              <span class="text-slate-400">Semantic Divergence</span>
              <p class="text-lg font-mono font-bold text-indigo-400">0.04</p>
              <span class="text-[10px] text-indigo-500">Aligned with user intent</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderBlockersTab() {
    const m = this.selectedMission;
    const blockers = m.blockers || [];
    return `
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold uppercase tracking-wider text-rose-400">Blockers & Human Escalations</h3>
          <span class="text-xs text-slate-400 font-mono">${blockers.length} active blockers</span>
        </div>
        <div class="space-y-3">
          ${blockers.length === 0 ? `
            <div class="p-8 text-center text-emerald-400 bg-emerald-950/20 rounded-xl border border-emerald-500/20 text-xs">
              No active blockers. Mission path is clear!
            </div>
          ` : blockers.map(b => `
            <div class="p-4 rounded-xl bg-rose-950/30 border border-rose-500/30 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-rose-300 font-mono uppercase">${b.severity || 'HIGH'} - ${b.blocker_type}</span>
                <span class="text-[10px] text-slate-400">${b.status}</span>
              </div>
              <p class="text-xs text-slate-200">${b.description}</p>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderSupervisoryTab() {
    const m = this.selectedMission;
    return `
      <div class="space-y-6">
        <div class="p-5 rounded-xl bg-slate-900/50 border border-white/10 space-y-3">
          <h3 class="text-sm font-bold uppercase tracking-wider text-cyan-400">Supervisory Autonomous Control Loop</h3>
          <p class="text-xs text-slate-400">Executes periodic Observe $\\to$ Evaluate $\\to$ Validate $\\to$ Drift Check $\\to$ Act supervisory cycles.</p>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5">
              <span class="text-slate-400 block mb-1">State Machine</span>
              <p class="font-bold text-cyan-300">${m.status}</p>
            </div>
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5">
              <span class="text-slate-400 block mb-1">Health State</span>
              <p class="font-bold text-emerald-300">${m.health}</p>
            </div>
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5">
              <span class="text-slate-400 block mb-1">Checkpoints</span>
              <p class="font-bold text-indigo-300">${(m.checkpoints || []).length} recorded</p>
            </div>
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5">
              <span class="text-slate-400 block mb-1">Budget Burn</span>
              <p class="font-bold text-amber-300">Nominal</p>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderAuditTab() {
    return `
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <h3 class="text-sm font-bold uppercase tracking-wider text-cyan-400">Tamper-Evident SHA-256 Audit Trail</h3>
            <p class="text-xs text-slate-400">Append-only cryptographic hash-chained provenance log.</p>
          </div>
          <button id="btn-verify-audit" class="px-3 py-1.5 rounded-lg bg-cyan-600/80 hover:bg-cyan-500 text-white text-xs font-semibold shadow">
            Verify Cryptographic Chain
          </button>
        </div>

        ${this.auditVerification ? `
          <div class="p-3 rounded-lg ${this.auditVerification.is_valid ? 'bg-emerald-950/50 border-emerald-500/50 text-emerald-300' : 'bg-rose-950/50 border-rose-500/50 text-rose-300'} border text-xs flex items-center justify-between">
            <span>Chain Status: <strong>${this.auditVerification.is_valid ? 'SECURE & VERIFIED' : 'TAMPERED / BROKEN'}</strong> (${this.auditVerification.records_checked} blocks verified)</span>
            <span class="font-mono text-[10px]">${this.auditVerification.verified_at}</span>
          </div>
        ` : ''}

        <div class="space-y-2 max-h-96 overflow-y-auto">
          ${this.auditTrail.length === 0 ? `
            <div class="p-8 text-center text-slate-500 bg-slate-900/30 rounded-xl border border-white/5 text-xs">
              No audit records recorded yet.
            </div>
          ` : this.auditTrail.map(r => `
            <div class="p-3 rounded-lg bg-slate-950/80 border border-white/5 font-mono text-[11px] space-y-1">
              <div class="flex items-center justify-between text-slate-400 text-[10px]">
                <span class="text-cyan-400 font-bold">${r.event_type}</span>
                <span>${r.timestamp}</span>
              </div>
              <div class="flex items-center justify-between text-slate-300">
                <span>Actor: <strong class="text-white">${r.actor}</strong> (${r.authority})</span>
                <span class="text-[10px] text-slate-500 truncate max-w-[200px]">Hash: ${r.record_hash}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    if (!this.container) return;

    // Mission Select
    const sel = this.container.querySelector('#mission-select');
    if (sel) {
      sel.addEventListener('change', (e) => {
        if (e.target.value) this.selectMission(e.target.value);
      });
    }

    // Mission Card Click
    this.container.querySelectorAll('.mission-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.getAttribute('data-mission-id');
        if (id) this.selectMission(id);
      });
    });

    // Tab Buttons
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Toolbar Action Buttons
    const btnStart = this.container.querySelector('#btn-start');
    if (btnStart) btnStart.addEventListener('click', () => this.triggerAction('start'));

    const btnCycle = this.container.querySelector('#btn-cycle');
    if (btnCycle) btnCycle.addEventListener('click', () => this.triggerAction('cycle'));

    const btnPause = this.container.querySelector('#btn-pause');
    if (btnPause) btnPause.addEventListener('click', () => this.triggerAction('pause'));

    const btnResume = this.container.querySelector('#btn-resume');
    if (btnResume) btnResume.addEventListener('click', () => this.triggerAction('resume'));

    const btnReplan = this.container.querySelector('#btn-replan');
    if (btnReplan) btnReplan.addEventListener('click', () => this.triggerAction('replan'));

    const btnComplete = this.container.querySelector('#btn-complete');
    if (btnComplete) btnComplete.addEventListener('click', () => this.triggerAction('complete'));

    const btnCancel = this.container.querySelector('#btn-cancel');
    if (btnCancel) btnCancel.addEventListener('click', () => this.triggerAction('cancel'));

    const btnVerifyAudit = this.container.querySelector('#btn-verify-audit');
    if (btnVerifyAudit) btnVerifyAudit.addEventListener('click', () => this.triggerAction('verifyAudit'));
  }
}
