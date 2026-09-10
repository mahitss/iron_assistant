/**
 * Kairo Executive Memory & Long-Horizon Context View (Task 53)
 * Provides comprehensive dashboard for:
 * - Executive Brief (CURRENT, RECENT, OPEN, BLOCKED, NEXT, RISKS, DECISIONS)
 * - 8 Canonical Continuity Query Explorer
 * - Open Loops & Blocker Tracking with Causal Evidence
 * - Authoritative Timeline & Time-Travel "As-Of" Historical State Reconstruction
 */

import { Endpoints } from '../../lib/api/endpoints.js';

export class ExecutiveMemoryView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'brief';
    this.projectId = 'default_project';
    this.state = null;
    this.brief = null;
    this.openLoops = [];
    this.blockers = [];
    this.timelineEvents = [];
    this.metrics = null;
    this.queryResult = null;
    this.asOfResult = null;
    this.isLoading = false;
  }

  formatDate(isoStr) {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  async init() {
    this.renderSkeleton();
    await this.loadAll();
  }

  async loadAll() {
    this.isLoading = true;
    try {
      const [stateRes, briefRes, loopsRes, blockersRes, timelineRes, metricsRes] = await Promise.allSettled([
        Endpoints.getExecutiveState(),
        Endpoints.getExecutiveBrief(this.projectId),
        Endpoints.listExecutiveOpenLoops({ project_id: this.projectId }),
        Endpoints.listExecutiveBlockers({ project_id: this.projectId }),
        Endpoints.listExecutiveTimeline({ project_id: this.projectId, limit: 20 }),
        Endpoints.getExecutiveMemoryMetrics(),
      ]);

      if (stateRes.status === 'fulfilled' && stateRes.value) this.state = stateRes.value;
      if (briefRes.status === 'fulfilled' && briefRes.value) this.brief = briefRes.value;
      if (loopsRes.status === 'fulfilled' && Array.isArray(loopsRes.value)) this.openLoops = loopsRes.value;
      if (blockersRes.status === 'fulfilled' && Array.isArray(blockersRes.value)) this.blockers = blockersRes.value;
      if (timelineRes.status === 'fulfilled' && Array.isArray(timelineRes.value)) this.timelineEvents = timelineRes.value;
      if (metricsRes.status === 'fulfilled' && metricsRes.value) this.metrics = metricsRes.value;
    } catch (err) {
      console.error('Failed to load executive memory:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  renderSkeleton() {
    this.container.innerHTML = `
      <div class="executive-memory-view" style="padding: 24px; color: var(--text-primary, #e2e8f0); font-family: system-ui, -apple-system, sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
          <div>
            <h2 style="margin: 0; font-size: 1.6rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Executive Memory & Long-Horizon Context
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: var(--text-muted, #94a3b8);">
              Authoritative continuity, causal timelines, open-loop tracking, and zero-leakage state reconstruction.
            </p>
          </div>
        </div>
        <div style="padding: 48px; text-align: center; color: var(--text-muted, #94a3b8);">
          Loading Executive State...
        </div>
      </div>
    `;
  }

  render() {
    const activeLoopsCount = this.openLoops.filter(l => l.status === 'OPEN').length;
    const activeBlockersCount = this.blockers.filter(b => b.status === 'ACTIVE').length;
    const falseContinuityRate = this.metrics ? (this.metrics.false_continuity_rate * 100).toFixed(1) + '%' : '0.0%';

    this.container.innerHTML = `
      <div class="executive-memory-view" style="padding: 24px; color: var(--text-primary, #e2e8f0); font-family: system-ui, -apple-system, sans-serif;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
          <div>
            <h2 style="margin: 0; font-size: 1.6rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Executive Memory & Continuity
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: var(--text-muted, #94a3b8);">
              HISTORY → EVENTS → STATE CHANGES → DECISIONS → OUTCOMES → CURRENT STATE → OPEN LOOPS → NEXT OBJECTIVES
            </p>
          </div>

          <div style="display: flex; align-items: center; gap: 12px;">
            <select id="em-project-selector" style="background: var(--bg-card, #1e293b); color: #e2e8f0; border: 1px solid var(--border, #334155); border-radius: 6px; padding: 6px 12px; font-size: 0.85rem;">
              <option value="default_project" ${this.projectId === 'default_project' ? 'selected' : ''}>Default Project</option>
              <option value="kairo_engine" ${this.projectId === 'kairo_engine' ? 'selected' : ''}>Kairo Core Engine</option>
            </select>
            <button id="em-refresh-btn" style="background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: 600; cursor: pointer; font-size: 0.85rem;">
              Refresh
            </button>
          </div>
        </div>

        <!-- Metrics Row -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Active Open Loops</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #38bdf8; margin-top: 4px;">${activeLoopsCount}</div>
          </div>
          <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Active Blockers</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: ${activeBlockersCount > 0 ? '#f87171' : '#34d399'}; margin-top: 4px;">${activeBlockersCount}</div>
          </div>
          <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Timeline Events</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #818cf8; margin-top: 4px;">${this.timelineEvents.length}</div>
          </div>
          <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">False Continuity Rate</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #34d399; margin-top: 4px;">${falseContinuityRate}</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border, #334155); margin-bottom: 24px;">
          <button class="em-tab-btn" data-tab="brief" style="padding: 10px 18px; border: none; background: none; color: ${this.activeTab === 'brief' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.activeTab === 'brief' ? '#38bdf8' : 'transparent'}; cursor: pointer; font-weight: 600; font-size: 0.9rem;">
            Executive Brief
          </button>
          <button class="em-tab-btn" data-tab="continuity" style="padding: 10px 18px; border: none; background: none; color: ${this.activeTab === 'continuity' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.activeTab === 'continuity' ? '#38bdf8' : 'transparent'}; cursor: pointer; font-weight: 600; font-size: 0.9rem;">
            Continuity Queries (8 Questions)
          </button>
          <button class="em-tab-btn" data-tab="loops" style="padding: 10px 18px; border: none; background: none; color: ${this.activeTab === 'loops' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.activeTab === 'loops' ? '#38bdf8' : 'transparent'}; cursor: pointer; font-weight: 600; font-size: 0.9rem;">
            Open Loops & Blockers
          </button>
          <button class="em-tab-btn" data-tab="timeline" style="padding: 10px 18px; border: none; background: none; color: ${this.activeTab === 'timeline' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.activeTab === 'timeline' ? '#38bdf8' : 'transparent'}; cursor: pointer; font-weight: 600; font-size: 0.9rem;">
            Timeline & As-Of Reconstruction
          </button>
        </div>

        <!-- Tab Content -->
        <div id="em-tab-content">
          ${this.renderTabContent()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderTabContent() {
    switch (this.activeTab) {
      case 'brief':
        return this.renderBriefTab();
      case 'continuity':
        return this.renderContinuityTab();
      case 'loops':
        return this.renderLoopsTab();
      case 'timeline':
        return this.renderTimelineTab();
      default:
        return '<div>Unknown Tab</div>';
    }
  }

  renderBriefTab() {
    const brief = this.brief;
    if (!brief) {
      return `
        <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 32px; text-align: center;">
          <p style="color: #94a3b8; margin-bottom: 16px;">No executive brief has been generated for this project yet.</p>
          <button id="em-generate-brief-btn" style="background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 8px 18px; font-weight: 600; cursor: pointer;">
            Generate Executive Brief
          </button>
        </div>
      `;
    }

    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
        <!-- Status & Next Steps -->
        <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; font-size: 1.05rem; color: #38bdf8;">Current Operational Status</h3>
            <span style="font-size: 0.75rem; background: #0f172a; padding: 4px 8px; border-radius: 4px; color: #94a3b8;">
              Updated ${this.formatDate(brief.created_at)}
            </span>
          </div>
          <p style="font-size: 0.92rem; line-height: 1.5; color: #cbd5e1; margin-bottom: 16px;">
            ${brief.current_status}
          </p>

          <h4 style="margin: 16px 0 8px 0; font-size: 0.9rem; color: #818cf8; text-transform: uppercase;">Next Actions</h4>
          ${brief.next_actions && brief.next_actions.length > 0 ? `
            <ul style="margin: 0; padding-left: 20px; font-size: 0.88rem; color: #cbd5e1;">
              ${brief.next_actions.map(a => `<li style="margin-bottom: 6px;">${a.objective || a.description || JSON.stringify(a)}</li>`).join('')}
            </ul>
          ` : '<p style="font-size: 0.85rem; color: #64748b;">No immediate next actions queued.</p>'}
        </div>

        <!-- Open Work & Blockers -->
        <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 20px;">
          <h3 style="margin: 0 0 12px 0; font-size: 1.05rem; color: #f87171;">Blockers & Open Work</h3>
          ${brief.blockers && brief.blockers.length > 0 ? `
            <div style="margin-bottom: 16px;">
              <span style="font-size: 0.8rem; font-weight: 700; color: #f87171;">Active Blockers:</span>
              <ul style="margin: 6px 0 0 0; padding-left: 20px; font-size: 0.88rem; color: #fca5a5;">
                ${brief.blockers.map(b => `<li style="margin-bottom: 4px;">${b.description || JSON.stringify(b)}</li>`).join('')}
              </ul>
            </div>
          ` : '<p style="font-size: 0.85rem; color: #34d399; margin-bottom: 16px;">✓ Zero active blockers.</p>'}

          <span style="font-size: 0.8rem; font-weight: 700; color: #94a3b8;">Open Loops:</span>
          ${brief.open_work && brief.open_work.length > 0 ? `
            <ul style="margin: 6px 0 0 0; padding-left: 20px; font-size: 0.88rem; color: #cbd5e1;">
              ${brief.open_work.map(w => `<li style="margin-bottom: 4px;">${w.description || JSON.stringify(w)}</li>`).join('')}
            </ul>
          ` : '<p style="font-size: 0.85rem; color: #64748b;">No unresolved open loops.</p>'}
        </div>

        <!-- Recent Decisions & Risks -->
        <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 20px; grid-column: 1 / -1;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
              <h3 style="margin: 0 0 12px 0; font-size: 1.05rem; color: #e2e8f0;">Recent Decisions</h3>
              ${brief.decisions && brief.decisions.length > 0 ? `
                <ul style="margin: 0; padding-left: 20px; font-size: 0.88rem; color: #cbd5e1;">
                  ${brief.decisions.map(d => `<li style="margin-bottom: 6px;"><strong>${d.summary || 'Decision'}:</strong> ${d.rationale || ''}</li>`).join('')}
                </ul>
              ` : '<p style="font-size: 0.85rem; color: #64748b;">No recent decisions recorded.</p>'}
            </div>
            <div>
              <h3 style="margin: 0 0 12px 0; font-size: 1.05rem; color: #e2e8f0;">Identified Risks</h3>
              ${brief.risks && brief.risks.length > 0 ? `
                <ul style="margin: 0; padding-left: 20px; font-size: 0.88rem; color: #cbd5e1;">
                  ${brief.risks.map(r => `<li style="margin-bottom: 6px;">${r.description || JSON.stringify(r)}</li>`).join('')}
                </ul>
              ` : '<p style="font-size: 0.85rem; color: #64748b;">No active risks surfaced.</p>'}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderContinuityTab() {
    return `
      <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 24px;">
        <h3 style="margin: 0 0 8px 0; font-size: 1.15rem; color: #38bdf8;">Continuity Query Explorer</h3>
        <p style="margin: 0 0 20px 0; font-size: 0.85rem; color: #94a3b8;">
          Ask the 8 canonical continuity questions grounded in authoritative system evidence without hallucination.
        </p>

        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
          <button class="em-q-preset" data-q="WHAT_WERE_WE_DOING" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">What were we doing?</button>
          <button class="em-q-preset" data-q="WHY_DID_WE_DO_IT" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">Why did we do it?</button>
          <button class="em-q-preset" data-q="WHERE_DID_WE_STOP" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">Where did we stop?</button>
          <button class="em-q-preset" data-q="WHAT_CHANGED" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">What changed?</button>
          <button class="em-q-preset" data-q="WHAT_IS_HAPPENING" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">What is currently happening?</button>
          <button class="em-q-preset" data-q="WHAT_REMAINS" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">What remains unfinished?</button>
          <button class="em-q-preset" data-q="WHAT_SHOULD_HAPPEN_NEXT" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">What should happen next?</button>
          <button class="em-q-preset" data-q="WHAT_IS_BLOCKING_US" style="background: #0f172a; border: 1px solid #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;">What is blocking us?</button>
        </div>

        <div style="display: flex; gap: 12px; margin-bottom: 20px;">
          <input id="em-custom-intent" type="text" placeholder="Optional explicit user intent override (e.g. 'prioritize tests')" style="flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; color: #e2e8f0; font-size: 0.88rem;" />
          <button id="em-run-query-btn" style="background: #38bdf8; color: #0f172a; font-weight: 700; border: none; border-radius: 6px; padding: 8px 18px; cursor: pointer;">
            Execute Query
          </button>
        </div>

        <!-- Query Output -->
        <div id="em-query-output" style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 16px; min-height: 120px;">
          ${this.queryResult ? `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-weight: 700; color: #38bdf8; font-size: 0.95rem;">${this.queryResult.question_type}</span>
              <span style="font-size: 0.75rem; background: #1e293b; padding: 2px 8px; border-radius: 4px; color: #94a3b8;">
                Confidence: ${this.queryResult.confidence_level}
              </span>
            </div>
            <p style="font-size: 0.92rem; color: #e2e8f0; margin-bottom: 12px; line-height: 1.5;">${this.queryResult.answer}</p>
            <div style="font-size: 0.78rem; color: #64748b;">
              <strong>Authoritative Sources:</strong> ${this.queryResult.authoritative_sources ? this.queryResult.authoritative_sources.join(', ') : 'None'}
            </div>
          ` : '<p style="color: #64748b; font-size: 0.88rem; margin: 0;">Select a preset or enter a query above to inspect continuity response.</p>'}
        </div>
      </div>
    `;
  }

  renderLoopsTab() {
    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <!-- Open Loops Column -->
        <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0; font-size: 1.05rem; color: #38bdf8;">Unfinished Open Loops</h3>
            <span style="font-size: 0.8rem; color: #94a3b8;">${this.openLoops.length} total</span>
          </div>

          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${this.openLoops.length > 0 ? this.openLoops.map(loop => `
              <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="font-size: 0.75rem; background: ${loop.status === 'STALE' ? '#854d0e' : '#1e3a8a'}; color: #93c5fd; padding: 2px 6px; border-radius: 4px;">
                    ${loop.status}
                  </span>
                  <span style="font-size: 0.75rem; color: #64748b;">Owner: ${loop.owner}</span>
                </div>
                <div style="font-size: 0.88rem; color: #e2e8f0; margin-bottom: 8px;">${loop.description}</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 0.75rem; color: #64748b;">Age: ${loop.age_days}d</span>
                  ${loop.status !== 'COMPLETED' ? `
                    <button class="em-close-loop-btn" data-loop-id="${loop.loop_id}" style="background: #22c55e; color: white; border: none; border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; cursor: pointer;">
                      Close Loop
                    </button>
                  ` : ''}
                </div>
              </div>
            `).join('') : '<p style="color: #64748b; font-size: 0.88rem;">No open loops found.</p>'}
          </div>
        </div>

        <!-- Blockers Column -->
        <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0; font-size: 1.05rem; color: #f87171;">Blockers & Dependencies</h3>
            <span style="font-size: 0.8rem; color: #94a3b8;">${this.blockers.length} total</span>
          </div>

          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${this.blockers.length > 0 ? this.blockers.map(b => `
              <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="font-size: 0.75rem; background: ${b.status === 'ACTIVE' ? '#991b1b' : '#065f46'}; color: #fecaca; padding: 2px 6px; border-radius: 4px;">
                    ${b.status} (${b.severity})
                  </span>
                  <span style="font-size: 0.75rem; color: #64748b;">Source: ${b.source}</span>
                </div>
                <div style="font-size: 0.88rem; color: #e2e8f0; margin-bottom: 6px;">${b.description}</div>
                <div style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 8px;">
                  <strong>Causality Proof:</strong> ${b.causality_evidence || 'N/A'}
                </div>
                ${b.status === 'ACTIVE' ? `
                  <button class="em-resolve-blocker-btn" data-blocker-id="${b.blocker_id}" style="background: #3b82f6; color: white; border: none; border-radius: 4px; padding: 3px 10px; font-size: 0.75rem; cursor: pointer;">
                    Resolve Blocker
                  </button>
                ` : ''}
              </div>
            `).join('') : '<p style="color: #64748b; font-size: 0.88rem;">No blockers recorded.</p>'}
          </div>
        </div>
      </div>
    `;
  }

  renderTimelineTab() {
    return `
      <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 8px; padding: 20px;">
        <!-- As-Of Time-Travel Controls -->
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 16px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
          <label style="font-size: 0.85rem; color: #94a3b8;">As-Of Historical Point:</label>
          <input id="em-as-of-date" type="datetime-local" style="background: #1e293b; border: 1px solid #334155; border-radius: 4px; color: #e2e8f0; padding: 6px 10px; font-size: 0.85rem;" />
          <button id="em-reconstruct-btn" style="background: #818cf8; color: white; border: none; border-radius: 4px; padding: 6px 14px; font-size: 0.85rem; font-weight: 600; cursor: pointer;">
            Reconstruct Historical State
          </button>
        </div>

        ${this.asOfResult ? `
          <div style="background: #1e293b; border: 1px solid #38bdf8; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
            <h4 style="margin: 0 0 8px 0; color: #38bdf8; font-size: 0.95rem;">Historical Reconstruction as of ${this.formatDate(this.asOfResult.as_of)}</h4>
            <div style="font-size: 0.85rem; color: #cbd5e1;">
              <strong>Events Included:</strong> ${this.asOfResult.events_applied_count} |
              <strong>Known Active Tasks:</strong> ${this.asOfResult.active_tasks ? this.asOfResult.active_tasks.length : 0} |
              <strong>Decisions Made:</strong> ${this.asOfResult.decisions_made ? this.asOfResult.decisions_made.length : 0}
            </div>
          </div>
        ` : ''}

        <!-- Chronological Timeline List -->
        <h3 style="margin: 0 0 16px 0; font-size: 1.05rem; color: #e2e8f0;">Chronological Event Feed</h3>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${this.timelineEvents.length > 0 ? this.timelineEvents.map(ev => `
            <div style="display: flex; gap: 12px; border-left: 2px solid #3b82f6; padding-left: 12px;">
              <div style="min-width: 140px; font-size: 0.75rem; color: #64748b;">
                ${this.formatDate(ev.timestamp)}
              </div>
              <div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #38bdf8;">
                  ${ev.event_type} <span style="font-size: 0.75rem; color: #94a3b8; font-weight: normal;">(${ev.source})</span>
                </div>
                <div style="font-size: 0.88rem; color: #e2e8f0; margin-top: 2px;">
                  ${ev.description_reference}
                </div>
              </div>
            </div>
          `).join('') : '<p style="color: #64748b; font-size: 0.88rem;">No timeline events recorded.</p>'}
        </div>
      </div>
    `;
  }

  bindEvents() {
    // Tab switching
    this.container.querySelectorAll('.em-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.activeTab = e.currentTarget.getAttribute('data-tab');
        this.render();
      });
    });

    // Refresh
    const refreshBtn = this.container.querySelector('#em-refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadAll());
    }

    // Project selector
    const projSelect = this.container.querySelector('#em-project-selector');
    if (projSelect) {
      projSelect.addEventListener('change', (e) => {
        this.projectId = e.target.value;
        this.loadAll();
      });
    }

    // Continuity query presets
    this.container.querySelectorAll('.em-q-preset').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const qType = e.currentTarget.getAttribute('data-q');
        const customIntent = this.container.querySelector('#em-custom-intent')?.value || null;
        try {
          this.queryResult = await Endpoints.queryExecutiveContinuity({
            question_type: qType,
            project_id: this.projectId,
            explicit_user_intent: customIntent,
          });
          this.render();
        } catch (err) {
          console.error('Continuity query failed:', err);
        }
      });
    });

    // Close open loop
    this.container.querySelectorAll('.em-close-loop-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const loopId = e.currentTarget.getAttribute('data-loop-id');
        const evidence = prompt('Enter closure evidence (required):');
        if (evidence) {
          await Endpoints.closeExecutiveOpenLoop(loopId, { evidence });
          await this.loadAll();
        }
      });
    });

    // Resolve blocker
    this.container.querySelectorAll('.em-resolve-blocker-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const blockerId = e.currentTarget.getAttribute('data-blocker-id');
        const evidence = prompt('Enter resolution evidence (required):');
        if (evidence) {
          await Endpoints.resolveExecutiveBlocker(blockerId, { resolution_evidence: evidence });
          await this.loadAll();
        }
      });
    });

    // Reconstruct As-Of
    const reconBtn = this.container.querySelector('#em-reconstruct-btn');
    if (reconBtn) {
      reconBtn.addEventListener('click', async () => {
        const dateInput = this.container.querySelector('#em-as-of-date')?.value;
        if (!dateInput) {
          alert('Please select a date and time.');
          return;
        }
        try {
          const iso = new Date(dateInput).toISOString();
          this.asOfResult = await Endpoints.reconstructExecutiveAsOf({
            as_of: iso,
            project_id: this.projectId,
          });
          this.render();
        } catch (err) {
          console.error('Reconstruction failed:', err);
        }
      });
    }

    // Generate brief
    const genBriefBtn = this.container.querySelector('#em-generate-brief-btn');
    if (genBriefBtn) {
      genBriefBtn.addEventListener('click', async () => {
        await Endpoints.generateExecutiveBrief(this.projectId, {
          current_status: 'Executive memory initialized; active sprint in progress.',
          recent_progress: [{ summary: 'Subsystem modules implemented and verified' }],
          open_work: [{ description: 'Complete full regression test suite' }],
        });
        await this.loadAll();
      });
    }
  }
}
