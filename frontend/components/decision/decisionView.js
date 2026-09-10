/**
 * Kairo Executive Decision Engine Component (Task 57).
 * Glassmorphic Decision Support Center UI.
 * Enforces: Recommendation != Decision != Approval != Execution != Verification.
 */

export class DecisionView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api;
    this.state = {
      activeTab: 'requests', // 'requests' | 'ranking' | 'tradeoffs' | 'explain' | 'gates' | 'calibration'
      decisions: [],
      currentDecision: null,
      explanation: null,
      calibration: null,
      isLoading: false,
      error: null,
      questionInput: '',
      intentInput: '',
    };
  }

  async render() {
    if (!this.container) return;
    this.container.innerHTML = this._template();
    this._attachEventListeners();
    await this.fetchData();
  }

  async fetchData() {
    this.state.isLoading = true;
    try {
      if (this.api && this.api.list) {
        const list = await this.api.list(50);
        this.state.decisions = list || [];
        if (this.state.decisions.length > 0 && !this.state.currentDecision) {
          this.state.currentDecision = this.state.decisions[this.state.decisions.length - 1];
        }
      }
      if (this.api && this.api.getAnalytics) {
        this.state.calibration = await this.api.getAnalytics();
      }
    } catch (err) {
      this.state.error = err.message || 'Failed to load decisions.';
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }

  _template() {
    return `
      <div class="decision-center-dashboard" style="display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem; background: #0b0f19; color: #f1f5f9; font-family: Inter, system-ui, sans-serif; min-height: 100vh;">
        <!-- Top Header & Advisory Banner -->
        <header style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 1rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #60a5fa, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Kairo Executive Decision Engine
              </h1>
              <span style="font-size: 0.75rem; background: #3b82f6; color: white; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                DECISION_SUPPORT_SYSTEM
              </span>
            </div>
            <p style="margin: 0.25rem 0 0; font-size: 0.875rem; color: #94a3b8;">
              Ranked, explainable, uncertainty-aware recommendations synthesized across state, goals, constraints, simulations, and causal evidence.
            </p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button id="btn-revalidate-decision" style="background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem;">
              🔄 Revalidate
            </button>
            <button id="btn-new-decision" style="background: linear-gradient(135deg, #2563eb, #7c3aed); border: none; color: white; padding: 0.5rem 1.25rem; border-radius: 0.375rem; cursor: pointer; font-weight: 600; font-size: 0.875rem;">
              ✨ Deliberate New Question
            </button>
          </div>
        </header>

        <!-- Advisory Invariant Notice -->
        <div style="background: rgba(30, 41, 59, 0.5); border-left: 4px solid #3b82f6; padding: 0.75rem 1rem; border-radius: 0.375rem; font-size: 0.8125rem; color: #cbd5e1;">
          <strong>Core Invariant:</strong> Recommendation &ne; Decision &ne; Approval &ne; Execution &ne; Verification. Kairo advises; human or policy authority decides.
        </div>

        <!-- Navigation Tabs -->
        <nav style="display: flex; gap: 0.5rem; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem;">
          ${this._renderTabBtn('requests', 'Decisions & Requests')}
          ${this._renderTabBtn('ranking', 'Ranked Options & Scores')}
          ${this._renderTabBtn('tradeoffs', 'Pareto Trade-Offs')}
          ${this._renderTabBtn('explain', 'Structured Explanations')}
          ${this._renderTabBtn('gates', 'Decision Gates & Approvals')}
          ${this._renderTabBtn('calibration', 'Quality & Calibration')}
        </nav>

        <!-- Main Dynamic Content Area -->
        <main id="decision-content-area" style="flex: 1;">
          <!-- Dynamically populated via _updateContent -->
        </main>
      </div>
    `;
  }

  _renderTabBtn(tabKey, label) {
    const isActive = this.state.activeTab === tabKey;
    const bg = isActive ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(168, 85, 247, 0.2))' : 'transparent';
    const border = isActive ? '1px solid #3b82f6' : '1px solid transparent';
    const color = isActive ? '#93c5fd' : '#94a3b8';
    return `
      <button class="nav-tab-btn" data-tab="${tabKey}" style="background: ${bg}; border: ${border}; color: ${color}; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-weight: 500; font-size: 0.875rem; transition: all 0.2s;">
        ${label}
      </button>
    `;
  }

  _attachEventListeners() {
    if (!this.container) return;

    this.container.querySelectorAll('.nav-tab-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        this.state.activeTab = e.currentTarget.getAttribute('data-tab');
        this.container.querySelectorAll('.nav-tab-btn').forEach((b) => {
          b.style.background = 'transparent';
          b.style.border = '1px solid transparent';
          b.style.color = '#94a3b8';
        });
        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(168, 85, 247, 0.2))';
        e.currentTarget.style.border = '1px solid #3b82f6';
        e.currentTarget.style.color = '#93c5fd';
        this._updateContent();
      });
    });

    const newBtn = this.container.querySelector('#btn-new-decision');
    if (newBtn) {
      newBtn.addEventListener('click', () => this._handleNewDecisionPrompt());
    }

    const revalBtn = this.container.querySelector('#btn-revalidate-decision');
    if (revalBtn) {
      revalBtn.addEventListener('click', () => this._handleRevalidate());
    }
  }

  _updateContent() {
    const area = this.container.querySelector('#decision-content-area');
    if (!area) return;

    if (this.state.isLoading) {
      area.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: center; height: 300px; color: #94a3b8;">
          <span>⚡ Deliberating options and evaluating constraints...</span>
        </div>
      `;
      return;
    }

    if (this.state.error) {
      area.innerHTML = `
        <div style="background: rgba(220, 38, 38, 0.2); border: 1px solid #ef4444; color: #fca5a5; padding: 1rem; border-radius: 0.5rem;">
          <strong>Error:</strong> ${this.state.error}
        </div>
      `;
      return;
    }

    switch (this.state.activeTab) {
      case 'requests':
        area.innerHTML = this._renderRequestsTab();
        this._attachRequestsEvents();
        break;
      case 'ranking':
        area.innerHTML = this._renderRankingTab();
        this._attachRankingEvents();
        break;
      case 'tradeoffs':
        area.innerHTML = this._renderTradeoffsTab();
        break;
      case 'explain':
        area.innerHTML = this._renderExplainTab();
        this._attachExplainEvents();
        break;
      case 'gates':
        area.innerHTML = this._renderGatesTab();
        this._attachGatesEvents();
        break;
      case 'calibration':
        area.innerHTML = this._renderCalibrationTab();
        break;
      default:
        area.innerHTML = `<div>Unknown Tab</div>`;
    }
  }

  _renderRequestsTab() {
    const decs = this.state.decisions || [];
    const current = this.state.currentDecision;

    return `
      <div style="display: grid; grid-template-columns: 350px 1fr; gap: 1.5rem;">
        <!-- Left Column: Decision List -->
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
          <h3 style="margin: 0; font-size: 1rem; font-weight: 600; color: #cbd5e1;">Evaluated Decisions</h3>
          <div style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 600px; overflow-y: auto;">
            ${
              decs.length === 0
                ? `<p style="color: #64748b; font-size: 0.875rem;">No decisions recorded. Submit a query above.</p>`
                : decs
                    .map((d) => {
                      const isSelected = current && current.decision_id === d.decision_id;
                      const border = isSelected ? '1px solid #3b82f6' : '1px solid #1e293b';
                      const bg = isSelected ? 'rgba(59, 130, 246, 0.1)' : 'rgba(30, 41, 59, 0.4)';
                      return `
                        <div class="decision-card-item" data-id="${d.decision_id}" style="padding: 0.75rem; border-radius: 0.375rem; border: ${border}; background: ${bg}; cursor: pointer; transition: background 0.2s;">
                          <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; font-size: 0.875rem; color: #f1f5f9;">${d.decision_id}</span>
                            <span style="font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 9999px; background: #1e293b; color: #94a3b8;">${d.status}</span>
                          </div>
                          <div style="font-size: 0.8125rem; color: #94a3b8; margin-top: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ${d.recommendation ? d.recommendation.headline : 'Draft Analysis'}
                          </div>
                        </div>
                      `;
                    })
                    .join('')
            }
          </div>
        </div>

        <!-- Right Column: Decision Snapshot & Details -->
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.5rem;">
          ${
            !current
              ? `<p style="color: #64748b;">Select a decision from the list to inspect recommendations, provenance, and gates.</p>`
              : `
                <div style="display: flex; flex-direction: column; gap: 1.25rem;">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #1e293b; padding-bottom: 1rem;">
                    <div>
                      <h2 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #f8fafc;">
                        ${current.recommendation ? current.recommendation.headline : current.decision_id}
                      </h2>
                      <div style="font-size: 0.8125rem; color: #94a3b8; margin-top: 0.25rem;">
                        Status: <strong style="color: #60a5fa;">${current.status}</strong> | Override: <strong>${current.user_override ? 'YES' : 'NO'}</strong> | Confidence: <strong>${(current.confidence * 100).toFixed(0)}%</strong>
                      </div>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                      ${
                        current.approval_required && current.status === 'AWAITING_APPROVAL'
                          ? `<button id="btn-approve-current" style="background: #10b981; border: none; color: white; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; font-weight: 600;">Approve Recommendation</button>`
                          : ''
                      }
                    </div>
                  </div>

                  <!-- Recommendation Card -->
                  ${
                    current.recommendation
                      ? `
                      <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 0.5rem; padding: 1rem;">
                        <h4 style="margin: 0 0 0.5rem; font-size: 0.9375rem; color: #93c5fd;">Recommended Course of Action:</h4>
                        <p style="margin: 0 0 0.75rem; font-size: 0.875rem; line-height: 1.5; color: #e2e8f0;">${current.recommendation.why_selected}</p>
                        <div style="font-size: 0.8125rem; color: #cbd5e1;">
                          <strong>Worst-Case Downside:</strong> ${current.recommendation.worst_case_downside}
                        </div>
                      </div>
                    `
                      : ''
                  }

                  <!-- Factor Provenance -->
                  <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1rem;">
                    <h4 style="margin: 0 0 0.5rem; font-size: 0.875rem; color: #cbd5e1;">Cryptographic Factor Provenance:</h4>
                    <pre style="margin: 0; font-size: 0.75rem; color: #94a3b8; overflow-x: auto; background: #070b14; padding: 0.75rem; border-radius: 0.25rem;">${JSON.stringify(current.provenance, null, 2)}</pre>
                  </div>
                </div>
              `
          }
        </div>
      </div>
    `;
  }

  _renderRankingTab() {
    const current = this.state.currentDecision;
    if (!current || !current.ranking) {
      return `<p style="color: #64748b;">No ranking evaluations available for the selected decision.</p>`;
    }

    const ranked = current.ranking.ranked_options || [];

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #f1f5f9;">Ranked Candidate Options</h3>
            <p style="margin: 0.25rem 0 0; font-size: 0.8125rem; color: #94a3b8;">
              Deterministic scoring synthesis. High scores on soft objectives never override hard constraint disqualification.
            </p>
          </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${ranked
            .map((evalOpt) => {
              const isLeading = evalOpt.option_id === current.ranking.recommended_option_id;
              const isSelected = evalOpt.option_id === current.selected_option_id;
              const isFeasible = evalOpt.raw_score > 0.0;
              const border = isLeading ? '1px solid #3b82f6' : '1px solid #1e293b';
              const bg = isLeading ? 'rgba(59, 130, 246, 0.06)' : 'rgba(30, 41, 59, 0.3)';

              return `
                <div style="border: ${border}; background: ${bg}; border-radius: 0.5rem; padding: 1rem; display: flex; justify-content: space-between; align-items: center;">
                  <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                      <span style="font-weight: 700; font-size: 1rem; color: #f8fafc;">#${evalOpt.rank} ${evalOpt.name}</span>
                      ${isLeading ? `<span style="font-size: 0.75rem; background: #3b82f6; color: white; padding: 0.15rem 0.5rem; border-radius: 9999px;">RECOMMENDED</span>` : ''}
                      ${isSelected ? `<span style="font-size: 0.75rem; background: #10b981; color: white; padding: 0.15rem 0.5rem; border-radius: 9999px;">SELECTED</span>` : ''}
                      ${!isFeasible ? `<span style="font-size: 0.75rem; background: #ef4444; color: white; padding: 0.15rem 0.5rem; border-radius: 9999px;">DISQUALIFIED</span>` : ''}
                    </div>
                    <p style="margin: 0.25rem 0 0.5rem; font-size: 0.8125rem; color: #94a3b8;">${evalOpt.explanation}</p>
                    <div style="display: flex; gap: 1rem; font-size: 0.75rem; color: #cbd5e1;">
                      <span>Normalized Score: <strong>${evalOpt.normalized_score.toFixed(2)}</strong></span>
                      <span>Benefit: <strong>+${evalOpt.benefit_score.toFixed(2)}</strong></span>
                      <span>Risk Penalty: <strong>-${evalOpt.risk_penalty.toFixed(2)}</strong></span>
                      <span>Cost Penalty: <strong>-${evalOpt.cost_penalty.toFixed(2)}</strong></span>
                    </div>
                  </div>
                  <div>
                    <button class="btn-select-option" data-id="${evalOpt.option_id}" style="background: #1e293b; border: 1px solid #334155; color: #f1f5f9; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.8125rem;">
                      Select This Option
                    </button>
                  </div>
                </div>
              `;
            })
            .join('')}
        </div>
      </div>
    `;
  }

  _renderTradeoffsTab() {
    const current = this.state.currentDecision;
    if (!current || !current.ranking) {
      return `<p style="color: #64748b;">No trade-off data available.</p>`;
    }

    const tradeoffs = current.ranking.tradeoffs_summary || [];
    const dominated = current.ranking.dominated_option_ids || [];

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div>
          <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #f1f5f9;">Pareto Frontier & Multi-Objective Trade-Offs</h3>
          <p style="margin: 0.25rem 0 0; font-size: 0.8125rem; color: #94a3b8;">
            Exposes explicit tensions between conflicting dimensions (e.g. security vs. cost, speed vs. reliability).
          </p>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1rem;">
            <h4 style="margin: 0 0 0.75rem; font-size: 0.9375rem; color: #60a5fa;">Tension Analysis:</h4>
            ${
              tradeoffs.length === 0
                ? `<p style="color: #64748b; font-size: 0.8125rem;">No multi-objective tensions identified.</p>`
                : tradeoffs
                    .map(
                      (t) => `
                    <div style="background: #0f172a; border-left: 3px solid #60a5fa; padding: 0.5rem 0.75rem; margin-bottom: 0.5rem; border-radius: 0.25rem; font-size: 0.8125rem; color: #e2e8f0;">
                      ${t}
                    </div>
                  `
                    )
                    .join('')
            }
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1rem;">
            <h4 style="margin: 0 0 0.75rem; font-size: 0.9375rem; color: #f87171;">Dominated Options (Strictly Inferior):</h4>
            ${
              dominated.length === 0
                ? `<p style="color: #64748b; font-size: 0.8125rem;">All evaluated options are non-dominated (Pareto-optimal).</p>`
                : dominated
                    .map(
                      (id) => `
                    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 0.5rem 0.75rem; margin-bottom: 0.5rem; border-radius: 0.25rem; font-size: 0.8125rem; color: #fca5a5;">
                      <strong>Option ${id}</strong> is strictly dominated by another feasible alternative across all primary objectives.
                    </div>
                  `
                    )
                    .join('')
            }
          </div>
        </div>
      </div>
    `;
  }

  _renderExplainTab() {
    const current = this.state.currentDecision;
    if (!current) {
      return `<p style="color: #64748b;">Select a decision to query faithful explanations.</p>`;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div>
          <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #f1f5f9;">Faithful Explanation Engine</h3>
          <p style="margin: 0.25rem 0 0; font-size: 0.8125rem; color: #94a3b8;">
            Directly answers executive inquiries based on structured scoring data without hallucinated rationale.
          </p>
        </div>

        <div style="display: flex; gap: 0.5rem;">
          <input id="input-explain-query" type="text" placeholder="e.g. 'Why this option?' or 'What are the risks?' or 'Why not alternatives?'" style="flex: 1; background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 0.6rem 1rem; border-radius: 0.375rem; font-size: 0.875rem;" />
          <button id="btn-submit-explain" style="background: #3b82f6; border: none; color: white; padding: 0.6rem 1.25rem; border-radius: 0.375rem; cursor: pointer; font-weight: 600; font-size: 0.875rem;">
            Ask Kairo
          </button>
        </div>

        <div id="explain-response-area" style="background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem; min-height: 150px; font-size: 0.875rem; color: #cbd5e1;">
          ${
            this.state.explanation
              ? `
              <h4 style="margin: 0 0 0.5rem; color: #93c5fd;">Answer:</h4>
              <p style="margin: 0; line-height: 1.6;">${this.state.explanation.answer}</p>
            `
              : `<p style="color: #64748b; margin: 0;">Enter a question above to inspect decision rationale, alternatives comparison, and worst-case risks.</p>`
          }
        </div>
      </div>
    `;
  }

  _renderGatesTab() {
    const current = this.state.currentDecision;
    if (!current || !current.decision_gates) {
      return `<p style="color: #64748b;">No decision gate evaluations available.</p>`;
    }

    const gates = Object.values(current.decision_gates);

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div>
          <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #f1f5f9;">Ten Formal Decision Gates</h3>
          <p style="margin: 0.25rem 0 0; font-size: 0.8125rem; color: #94a3b8;">
            A recommendation may be generated without passing execution gates. Execution must NEVER proceed without required gates.
          </p>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem;">
          ${gates
            .map((gate) => {
              const isPassed = gate.status === 'PASSED';
              const isPending = gate.status === 'PENDING_APPROVAL';
              const statusColor = isPassed ? '#10b981' : isPending ? '#f59e0b' : '#ef4444';
              const bg = isPassed ? 'rgba(16, 185, 129, 0.05)' : isPending ? 'rgba(245, 158, 11, 0.05)' : 'rgba(239, 68, 68, 0.05)';

              return `
                <div style="background: ${bg}; border: 1px solid ${statusColor}; border-radius: 0.5rem; padding: 1rem;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-weight: 700; font-size: 0.875rem; color: #f1f5f9;">Gate ${gate.gate_number}: ${gate.name}</span>
                    <span style="font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 9999px; background: ${statusColor}; color: white; font-weight: 700;">
                      ${gate.status}
                    </span>
                  </div>
                  <p style="margin: 0; font-size: 0.8125rem; color: #cbd5e1; line-height: 1.4;">${gate.message}</p>
                </div>
              `;
            })
            .join('')}
        </div>
      </div>
    `;
  }

  _renderCalibrationTab() {
    const cal = this.state.calibration || {
      total_decisions: 0,
      acceptance_rate: 0.0,
      override_rate: 0.0,
      actual_success_rate: 0.0,
      average_confidence: 0.0,
      calibration_error: 0.0,
      calibration_assessment: 'NO_DATA',
    };

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div>
          <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #f1f5f9;">Decision Engine Quality & Calibration Analytics</h3>
          <p style="margin: 0.25rem 0 0; font-size: 0.8125rem; color: #94a3b8;">
            Compares confidence against actual post-execution reality. User acceptance alone does not define a good decision.
          </p>
        </div>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <div style="font-size: 0.75rem; color: #94a3b8;">TOTAL DECISIONS</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #f8fafc; margin-top: 0.25rem;">${cal.total_decisions}</div>
          </div>
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <div style="font-size: 0.75rem; color: #94a3b8;">OVERRIDE RATE</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #f87171; margin-top: 0.25rem;">${(cal.override_rate * 100).toFixed(1)}%</div>
          </div>
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <div style="font-size: 0.75rem; color: #94a3b8;">AVERAGE CONFIDENCE</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #60a5fa; margin-top: 0.25rem;">${(cal.average_confidence * 100).toFixed(1)}%</div>
          </div>
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <div style="font-size: 0.75rem; color: #94a3b8;">CALIBRATION STATUS</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #34d399; margin-top: 0.25rem;">${cal.calibration_assessment}</div>
          </div>
        </div>
      </div>
    `;
  }

  _attachRequestsEvents() {
    this.container.querySelectorAll('.decision-card-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        this.state.currentDecision = this.state.decisions.find((d) => d.decision_id === id);
        this._updateContent();
      });
    });

    const approveBtn = this.container.querySelector('#btn-approve-current');
    if (approveBtn) {
      approveBtn.addEventListener('click', async () => {
        if (!this.state.currentDecision) return;
        try {
          const updated = await this.api.approve(this.state.currentDecision.decision_id, {
            approver: 'admin_user',
            approval_id: 'appr_' + Math.random().toString(36).substring(7),
          });
          this.state.currentDecision = updated;
          await this.fetchData();
        } catch (err) {
          alert('Approval failed: ' + err.message);
        }
      });
    }
  }

  _attachRankingEvents() {
    this.container.querySelectorAll('.btn-select-option').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const optId = e.currentTarget.getAttribute('data-id');
        if (!this.state.currentDecision) return;
        try {
          const updated = await this.api.select(this.state.currentDecision.decision_id, {
            chosen_option_id: optId,
            actor: 'authorized_operator',
          });
          this.state.currentDecision = updated;
          await this.fetchData();
        } catch (err) {
          alert('Option selection failed: ' + err.message);
        }
      });
    });
  }

  _attachExplainEvents() {
    const submitBtn = this.container.querySelector('#btn-submit-explain');
    const input = this.container.querySelector('#input-explain-query');
    if (submitBtn && input) {
      submitBtn.addEventListener('click', async () => {
        const query = input.value.trim();
        if (!query || !this.state.currentDecision) return;
        try {
          const res = await this.api.explain(this.state.currentDecision.decision_id, query);
          this.state.explanation = res;
          this._updateContent();
        } catch (err) {
          alert('Query failed: ' + err.message);
        }
      });
    }
  }

  _attachGatesEvents() {
    // Event hooks for interactive gate inspections
  }

  async _handleNewDecisionPrompt() {
    const question = prompt('Enter the executive decision question:', 'What deployment strategy should we use?');
    if (!question) return;

    try {
      this.state.isLoading = true;
      this._updateContent();
      const payload = {
        request: {
          question,
          intent: 'DEPLOYMENT_STRATEGY',
          context_scope: 'PROJECT',
          risk_tolerance: 'MEDIUM',
        },
      };
      const res = await this.api.analyze(payload);
      this.state.currentDecision = res;
      await this.fetchData();
    } catch (err) {
      alert('Decision evaluation failed: ' + err.message);
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }

  async _handleRevalidate() {
    if (!this.state.currentDecision) return;
    try {
      this.state.isLoading = true;
      this._updateContent();
      const res = await this.api.revalidate(this.state.currentDecision.decision_id);
      this.state.currentDecision = res;
      await this.fetchData();
    } catch (err) {
      alert('Revalidation failed: ' + err.message);
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }
}
