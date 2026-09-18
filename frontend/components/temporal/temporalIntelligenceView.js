/**
 * TemporalIntelligenceView Component (Task 111)
 *
 * Interactive web component providing:
 * - "What Changed?" semantic state diff explorer (From / To)
 * - Chronological multi-clock timeline view
 * - State-at-Time ("As-Of") inspector
 * - Temporal Gaps & Anomalies monitor
 * - Watermark lag indicators
 */

export class TemporalIntelligenceView {
  constructor(options = {}) {
    this.api = options.api;
    this.container = options.container || null;
    this.activeTab = 'diff'; // 'diff' | 'timeline' | 'as-of' | 'diagnostics' | 'watermarks'
    this.selectedEntity = 'global';
    this.activeChangeset = null;
    this.timelineData = null;
    this.asOfResult = null;
    this.anomalies = [];
    this.gaps = [];
    this.watermarks = [];
    this.checkpoints = [];
  }

  async init(container) {
    if (container) this.container = container;
    if (!this.container) return;
    await this.refresh();
  }

  async refresh() {
    try {
      if (this.api) {
        const [anomsRes, gapsRes, wtmkRes, chkpRes] = await Promise.allSettled([
          this.api.listAnomalies(),
          this.api.listGaps(),
          this.api.listWatermarks(),
          this.api.listCheckpoints(),
        ]);
        if (anomsRes.status === 'fulfilled') this.anomalies = anomsRes.value || [];
        if (gapsRes.status === 'fulfilled') this.gaps = gapsRes.value || [];
        if (wtmkRes.status === 'fulfilled') this.watermarks = wtmkRes.value || [];
        if (chkpRes.status === 'fulfilled') this.checkpoints = chkpRes.value || [];

        // Load default timeline
        const tlRes = await this.api.getTimeline(this.selectedEntity);
        if (tlRes) this.timelineData = tlRes;
      }
    } catch (err) {
      console.warn('Failed to fetch initial temporal data:', err);
    }
    this.render();
  }

  render() {
    if (!this.container) return;
    this.container.innerHTML = this.template();
    this.attachEventListeners();
  }

  template() {
    return `
      <div class="temporal-intelligence-view" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #e2e8f0; background: #0f172a; border-radius: 12px; padding: 24px; box-shadow: 0 8px 32px rgba(0,0,0,0.36);">
        <!-- Header Banner -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 20px;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <span style="font-size: 24px;">⏱️</span>
              <h2 style="margin: 0; font-size: 20px; font-weight: 600; color: #f8fafc;">Kairo Temporal Intelligence & Event History</h2>
              <span style="background: #1e293b; color: #38bdf8; font-size: 11px; padding: 3px 8px; border-radius: 6px; border: 1px solid #0284c7;">Task 111</span>
            </div>
            <p style="margin: 4px 0 0 34px; color: #94a3b8; font-size: 13px;">
              Multi-clock reconciliation, state transitions, causal attribution & "What Changed?" analysis
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="btn-temp-checkpoint" style="background: #0284c7; color: #ffffff; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500;">
              📸 Capture Checkpoint
            </button>
            <button id="btn-temp-reconstruct" style="background: #334155; color: #f1f5f9; border: 1px solid #475569; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 13px;">
              🔄 Reconstruct Offline
            </button>
            <button id="btn-temp-refresh" style="background: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 7px 12px; border-radius: 6px; cursor: pointer; font-size: 13px;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Metric Badges Row -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">
          <div style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #38bdf8;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Recorded Events</div>
            <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
              ${this.timelineData ? this.timelineData.total_events : 0}
            </div>
          </div>
          <div style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #10b981;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">State Transitions</div>
            <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
              ${this.timelineData ? this.timelineData.total_transitions : 0}
            </div>
          </div>
          <div style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid ${this.anomalies.length > 0 ? '#f59e0b' : '#64748b'};">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Anomalies Detected</div>
            <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
              ${this.anomalies.length}
            </div>
          </div>
          <div style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid ${this.gaps.length > 0 ? '#ef4444' : '#64748b'};">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Temporal Gaps</div>
            <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-top: 2px;">
              ${this.gaps.length}
            </div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid #334155; margin-bottom: 20px;">
          ${this.renderTabButton('diff', '🔍 What Changed?')}
          ${this.renderTabButton('timeline', '📅 Chronological Timeline')}
          ${this.renderTabButton('as-of', '🕰️ State-at-Time (As-Of)')}
          ${this.renderTabButton('diagnostics', '⚠️ Gaps & Anomalies')}
          ${this.renderTabButton('watermarks', '🌊 Watermarks & Sync')}
        </div>

        <!-- Tab Body -->
        <div class="temporal-tab-body">
          ${this.renderTabContent()}
        </div>
      </div>
    `;
  }

  renderTabButton(tabKey, label) {
    const isActive = this.activeTab === tabKey;
    const style = isActive
      ? 'background: #0284c7; color: #ffffff; font-weight: 600;'
      : 'background: transparent; color: #94a3b8; font-weight: 500;';
    return `
      <button class="temporal-tab-btn" data-tab="${tabKey}" style="${style} border: none; padding: 8px 16px; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 13px; transition: all 0.2s;">
        ${label}
      </button>
    `;
  }

  renderTabContent() {
    switch (this.activeTab) {
      case 'diff':
        return this.renderDiffView();
      case 'timeline':
        return this.renderTimelineView();
      case 'as-of':
        return this.renderAsOfView();
      case 'diagnostics':
        return this.renderDiagnosticsView();
      case 'watermarks':
        return this.renderWatermarksView();
      default:
        return `<div style="color: #64748b;">Select a tab above.</div>`;
    }
  }

  renderDiffView() {
    return `
      <div>
        <div style="display: flex; gap: 16px; margin-bottom: 16px; align-items: flex-end;">
          <div style="flex: 1;">
            <label style="display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">Baseline State (FROM)</label>
            <input id="diff-from-ref" type="text" value="checkpoint_preflight" style="width: 100%; background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 8px 12px; border-radius: 6px; font-size: 13px;" />
          </div>
          <div style="flex: 1;">
            <label style="display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">Target State (TO)</label>
            <input id="diff-to-ref" type="text" value="checkpoint_verified" style="width: 100%; background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 8px 12px; border-radius: 6px; font-size: 13px;" />
          </div>
          <button id="btn-run-diff" style="background: #38bdf8; color: #0f172a; border: none; padding: 9px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 13px;">
            Compute Diff
          </button>
        </div>

        <div id="diff-results-panel">
          ${this.renderDiffResults()}
        </div>
      </div>
    `;
  }

  renderDiffResults() {
    if (!this.activeChangeset) {
      return `
        <div style="background: #1e293b; padding: 32px; text-align: center; border-radius: 8px; border: 1px dashed #334155; color: #94a3b8;">
          Enter baseline and target references above or trigger a diff to inspect semantic state changes.
        </div>
      `;
    }

    const cs = this.activeChangeset;
    return `
      <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <span style="font-weight: 600; color: #f8fafc;">Diff: ${cs.from_reference} ➔ ${cs.to_reference}</span>
          <span style="font-size: 12px; color: #94a3b8;">Total Changes: ${cs.changes.length}</span>
        </div>

        <div style="display: flex; gap: 8px; margin-bottom: 16px;">
          <span style="background: #064e3b; color: #6ee7b7; font-size: 11px; padding: 2px 8px; border-radius: 4px;">+${cs.added_count} Added</span>
          <span style="background: #7f1d1d; color: #fca5a5; font-size: 11px; padding: 2px 8px; border-radius: 4px;">-${cs.removed_count} Removed</span>
          <span style="background: #1e3a8a; color: #93c5fd; font-size: 11px; padding: 2px 8px; border-radius: 4px;">~${cs.modified_count} Modified</span>
          <span style="background: #78350f; color: #fde68a; font-size: 11px; padding: 2px 8px; border-radius: 4px;">⚠ ${cs.degraded_count} Degraded</span>
          <span style="background: #334155; color: #cbd5e1; font-size: 11px; padding: 2px 8px; border-radius: 4px;">? ${cs.unattributed_count} Unattributed</span>
        </div>

        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="border-bottom: 1px solid #334155; color: #94a3b8; text-align: left;">
              <th style="padding: 8px;">Attribute</th>
              <th style="padding: 8px;">Previous</th>
              <th style="padding: 8px;">New Value</th>
              <th style="padding: 8px;">Category</th>
              <th style="padding: 8px;">Attribution</th>
            </tr>
          </thead>
          <tbody>
            ${cs.changes.map(c => `
              <tr style="border-bottom: 1px solid #243248;">
                <td style="padding: 8px; font-family: monospace; color: #38bdf8;">${c.attribute_path}</td>
                <td style="padding: 8px; color: #fca5a5;">${c.previous_value !== null ? c.previous_value : '—'}</td>
                <td style="padding: 8px; color: #6ee7b7;">${c.new_value !== null ? c.new_value : '—'}</td>
                <td style="padding: 8px;">${this.renderCategoryBadge(c.category)}</td>
                <td style="padding: 8px; font-size: 11px; color: #94a3b8;">${c.attribution}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderTimelineView() {
    if (!this.timelineData || !this.timelineData.events.length) {
      return `
        <div style="background: #1e293b; padding: 32px; text-align: center; border-radius: 8px; color: #94a3b8;">
          No timeline events recorded yet.
        </div>
      `;
    }

    return `
      <div>
        <div style="display: flex; gap: 12px; margin-bottom: 16px;">
          <input id="timeline-filter-entity" type="text" placeholder="Filter by Entity ID..." value="${this.selectedEntity === 'global' ? '' : this.selectedEntity}" style="background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 7px 12px; border-radius: 6px; font-size: 13px; width: 260px;" />
          <button id="btn-filter-timeline" style="background: #334155; color: #f8fafc; border: 1px solid #475569; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 13px;">Filter</button>
        </div>

        <div style="position: relative; padding-left: 20px; border-left: 2px solid #334155;">
          ${this.timelineData.events.map(e => `
            <div style="margin-bottom: 20px; position: relative;">
              <div style="position: absolute; left: -27px; top: 2px; width: 12px; height: 12px; border-radius: 50%; background: #38bdf8; border: 2px solid #0f172a;"></div>
              <div style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border: 1px solid #334155;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                  <span style="font-weight: 600; color: #f8fafc;">${e.event_type}</span>
                  <span style="font-size: 11px; color: #94a3b8;">Event Time: ${new Date(e.clocks.event_time).toISOString()}</span>
                </div>
                <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 6px;">${e.payload_summary}</div>
                <div style="display: flex; gap: 8px; font-size: 11px; color: #94a3b8;">
                  <span>Source: <strong style="color: #f1f5f9;">${e.source_subsystem}</strong></span>
                  <span>Category: <strong style="color: #f1f5f9;">${e.category}</strong></span>
                  <span>Ingested Lag: <strong style="color: #f1f5f9;">${Math.max(0, (new Date(e.clocks.ingested_time) - new Date(e.clocks.event_time)) / 1000).toFixed(2)}s</strong></span>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderAsOfView() {
    return `
      <div>
        <!-- Notice banner -->
        <div style="background: #451a03; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;">
          <strong style="color: #fde68a;">HISTORICAL STATE RECONSTRUCTION INVARIANT:</strong>
          <span style="color: #fed7aa; font-size: 13px; margin-left: 6px;">
            Evaluated states reflect past beliefs/observations as-of timestamp. They must never masquerade as current state or authorize actions.
          </span>
        </div>

        <div style="display: flex; gap: 16px; align-items: flex-end; margin-bottom: 20px;">
          <div style="flex: 1;">
            <label style="display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">Target Entity ID</label>
            <input id="as-of-entity-id" type="text" placeholder="e.g. mission_123, capability_db" style="width: 100%; background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 8px 12px; border-radius: 6px; font-size: 13px;" />
          </div>
          <div style="flex: 1;">
            <label style="display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">Historical Timestamp (ISO)</label>
            <input id="as-of-timestamp" type="text" value="${new Date().toISOString()}" style="width: 100%; background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 8px 12px; border-radius: 6px; font-size: 13px;" />
          </div>
          <button id="btn-run-as-of" style="background: #0284c7; color: #ffffff; border: none; padding: 9px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 13px;">
            Evaluate State As-Of
          </button>
        </div>

        <div id="as-of-results-container">
          ${this.asOfResult ? this.renderAsOfResult(this.asOfResult) : `
            <div style="background: #1e293b; padding: 32px; text-align: center; border-radius: 8px; color: #94a3b8;">
              Specify entity and historical timestamp above to reconstruct point-in-time state.
            </div>
          `}
        </div>
      </div>
    `;
  }

  renderAsOfResult(res) {
    return `
      <div style="background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
          <span style="font-size: 16px; font-weight: 600; color: #f8fafc;">Entity: ${res.entity_id}</span>
          <span style="background: #78350f; color: #fde68a; font-size: 11px; padding: 3px 8px; border-radius: 4px;">PAST STATE</span>
        </div>
        <div style="font-size: 20px; font-weight: 700; color: #38bdf8; margin-bottom: 12px;">
          State: ${res.state}
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; font-size: 12px; color: #94a3b8;">
          <div>As-Of Query Time: <strong style="color: #f1f5f9;">${res.as_of_time}</strong></div>
          <div>Effective From: <strong style="color: #f1f5f9;">${res.effective_from || '—'}</strong></div>
          <div>Confidence: <strong style="color: #f1f5f9;">${(res.confidence * 100).toFixed(0)}%</strong></div>
        </div>
      </div>
    `;
  }

  renderDiagnosticsView() {
    return `
      <div>
        <h3 style="font-size: 15px; color: #f8fafc; margin-top: 0; margin-bottom: 12px;">Temporal Anomalies</h3>
        ${this.anomalies.length ? `
          <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px;">
            ${this.anomalies.map(a => `
              <div style="background: #1e293b; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <strong style="color: #fde68a;">${a.anomaly_type}</strong>
                  <span style="font-size: 11px; color: #94a3b8;">${new Date(a.detected_at).toISOString()}</span>
                </div>
                <div style="font-size: 13px; color: #cbd5e1;">${a.explanation}</div>
                ${a.remediation_suggested ? `<div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Suggestion: ${a.remediation_suggested}</div>` : ''}
              </div>
            `).join('')}
          </div>
        ` : `
          <div style="background: #1e293b; padding: 16px; border-radius: 6px; color: #10b981; margin-bottom: 24px;">
            ✓ No active timing anomalies detected.
          </div>
        `}

        <h3 style="font-size: 15px; color: #f8fafc; margin-bottom: 12px;">Unobserved Temporal Gaps</h3>
        ${this.gaps.length ? `
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${this.gaps.map(g => `
              <div style="background: #1e293b; border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 6px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <strong style="color: #fca5a5;">${g.subsystem} (Duration: ${g.duration_seconds.toFixed(1)}s)</strong>
                  <span style="font-size: 11px; color: #94a3b8;">${new Date(g.gap_start).toISOString()} ➔ ${new Date(g.gap_end).toISOString()}</span>
                </div>
                <div style="font-size: 13px; color: #cbd5e1;">${g.reason}</div>
              </div>
            `).join('')}
          </div>
        ` : `
          <div style="background: #1e293b; padding: 16px; border-radius: 6px; color: #10b981;">
            ✓ No telemetry gaps observed. Continuity verified.
          </div>
        `}
      </div>
    `;
  }

  renderWatermarksView() {
    return `
      <div>
        <p style="font-size: 13px; color: #94a3b8; margin-top: 0; margin-bottom: 16px;">
          Watermarks represent high-water marks of ingested and reconciled events across subsystems.
        </p>

        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">
          ${this.watermarks.map(w => `
            <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <strong style="color: #38bdf8;">${w.subsystem}</strong>
                <span style="font-size: 11px; color: #10b981;">SYNCED</span>
              </div>
              <div style="font-size: 12px; color: #cbd5e1; display: flex; flex-direction: column; gap: 6px;">
                <div>Source: <strong style="color: #f1f5f9;">${new Date(w.source_watermark).toISOString()}</strong></div>
                <div>Ingested: <strong style="color: #f1f5f9;">${new Date(w.ingestion_watermark).toISOString()}</strong></div>
                <div>Reconciled: <strong style="color: #f1f5f9;">${new Date(w.reconciliation_watermark).toISOString()}</strong></div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderCategoryBadge(category) {
    const map = {
      ADDED: '#064e3b; color: #6ee7b7',
      REMOVED: '#7f1d1d; color: #fca5a5',
      MODIFIED: '#1e3a8a; color: #93c5fd',
      DEGRADED: '#78350f; color: #fde68a',
      RECOVERED: '#065f46; color: #a7f3d0',
    };
    const style = map[category] || '#334155; color: #cbd5e1';
    return `<span style="background: ${style}; font-size: 11px; padding: 2px 6px; border-radius: 4px;">${category}</span>`;
  }

  attachEventListeners() {
    if (!this.container) return;

    // Tab buttons
    this.container.querySelectorAll('.temporal-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.activeTab = e.target.dataset.tab;
        this.render();
      });
    });

    // Refresh
    const btnRefresh = this.container.querySelector('#btn-temp-refresh');
    if (btnRefresh) btnRefresh.addEventListener('click', () => this.refresh());

    // Checkpoint
    const btnChkp = this.container.querySelector('#btn-temp-checkpoint');
    if (btnChkp) {
      btnChkp.addEventListener('click', async () => {
        const name = prompt('Enter checkpoint name:', `checkpoint_${Date.now()}`);
        if (name && this.api) {
          await this.api.createCheckpoint({ name });
          await this.refresh();
        }
      });
    }

    // Reconstruct
    const btnRecon = this.container.querySelector('#btn-temp-reconstruct');
    if (btnRecon) {
      btnRecon.addEventListener('click', async () => {
        if (this.api) {
          await this.api.reconstructOffline({ subsystem: 'telemetry' });
          await this.refresh();
        }
      });
    }

    // Diff button
    const btnDiff = this.container.querySelector('#btn-run-diff');
    if (btnDiff) {
      btnDiff.addEventListener('click', async () => {
        const fromRef = this.container.querySelector('#diff-from-ref').value;
        const toRef = this.container.querySelector('#diff-to-ref').value;
        if (this.api) {
          const res = await this.api.computeDiff({
            state_a: { health: 'READY', tasks: 3, latency: 12 },
            state_b: { health: 'DEGRADED', tasks: 5, latency: 85 },
            from_reference: fromRef,
            to_reference: toRef,
          });
          this.activeChangeset = res;
          this.render();
        }
      });
    }

    // As-Of button
    const btnAsOf = this.container.querySelector('#btn-run-as-of');
    if (btnAsOf) {
      btnAsOf.addEventListener('click', async () => {
        const entId = this.container.querySelector('#as-of-entity-id').value;
        const ts = this.container.querySelector('#as-of-timestamp').value;
        if (entId && this.api) {
          const res = await this.api.getStateAsOf(entId, ts);
          this.asOfResult = res;
          this.render();
        }
      });
    }
  }
}
