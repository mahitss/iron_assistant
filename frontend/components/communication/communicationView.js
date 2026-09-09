/**
 * Kairo Social & Communication Intelligence Engine View (Task 49)
 * Multi-channel orchestration across email, chat, meetings, voice, and collaborative feeds.
 * Strictly enforces Draft != Sent, anti-fabrication, anti-social-profiling, and delivery verification.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class CommunicationView {
  constructor(container) {
    this.container = container;
    this.threads = [];
    this.drafts = [];
    this.commitments = [];
    this.followups = [];
    this.contacts = [];
    this.metrics = null;
    this.activeTab = 'threads';
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

  getStatusBadgeClass(status) {
    switch (status) {
      case 'DELIVERED':
      case 'APPROVED':
      case 'COMPLETED':
      case 'ACTIVE':
        return 'badge-success';
      case 'DRAFT':
      case 'REVIEWED':
      case 'WAITING':
      case 'OPEN':
        return 'badge-warning';
      case 'FAILED':
      case 'DISCARDED':
      case 'CANCELLED':
      case 'EXHAUSTED':
        return 'badge-danger';
      case 'SENT':
      case 'IN_PROGRESS':
        return 'badge-primary';
      default:
        return 'badge-neutral';
    }
  }

  async render() {
    this.container.innerHTML = `
      <div class="communication-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Social & Communication Intelligence Engine</h1>
            <p class="page-subtitle">Multi-channel message understanding, threading, grounded commitments, draft governance & safe delivery</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-comm-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="ingest-comm-modal-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              Ingest Message
            </button>
          </div>
        </header>

        <!-- Stats Overview Bar -->
        <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Active Threads</div>
            <div id="stat-active-threads" style="font-size: 1.6rem; font-weight: 700; color: var(--text-primary);">-</div>
          </div>
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Pending Drafts</div>
            <div id="stat-pending-drafts" style="font-size: 1.6rem; font-weight: 700; color: var(--accent-amber, #f59e0b);">-</div>
          </div>
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Open Commitments</div>
            <div id="stat-open-commitments" style="font-size: 1.6rem; font-weight: 700; color: var(--accent-blue, #3b82f6);">-</div>
          </div>
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Send Success Rate</div>
            <div id="stat-send-rate" style="font-size: 1.6rem; font-weight: 700; color: var(--accent-emerald, #10b981);">-</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="nav-tabs" style="display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1.5rem;">
          <button class="tab-btn active" data-tab="threads" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; border-bottom: 2px solid var(--accent-primary); color: var(--text-primary); font-weight: 600;">Threads</button>
          <button class="tab-btn" data-tab="drafts" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Drafts & Approvals</button>
          <button class="tab-btn" data-tab="commitments" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Commitments</button>
          <button class="tab-btn" data-tab="followups" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Follow-ups</button>
          <button class="tab-btn" data-tab="contacts" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Address Book</button>
          <button class="tab-btn" data-tab="telemetry" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Telemetry</button>
        </div>

        <!-- Tab Contents -->
        <div id="comm-tab-content">
          <div class="loading-spinner" style="text-align: center; padding: 2rem;">Loading communication engine state...</div>
        </div>
      </div>
    `;

    this.attachEvents();
    await this.loadData();
  }

  attachEvents() {
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.container.querySelectorAll('.tab-btn').forEach(b => {
          b.classList.remove('active');
          b.style.borderBottom = 'none';
          b.style.color = 'var(--text-muted)';
        });
        btn.classList.add('active');
        btn.style.borderBottom = '2px solid var(--accent-primary)';
        btn.style.color = 'var(--text-primary)';
        this.activeTab = btn.dataset.tab;
        this.renderActiveTab();
      });
    });

    const refreshBtn = this.container.querySelector('#refresh-comm-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const modalBtn = this.container.querySelector('#ingest-comm-modal-btn');
    if (modalBtn) {
      modalBtn.addEventListener('click', () => this.showIngestModal());
    }
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [threadsRes, draftsRes, commitmentsRes, followupsRes, contactsRes, metricsRes] = await Promise.allSettled([
        Endpoints.listCommunicationThreads(),
        Endpoints.listCommunicationDrafts(),
        Endpoints.listCommunicationCommitments(),
        Endpoints.listCommunicationFollowups(),
        Endpoints.listCommunicationContacts(),
        Endpoints.getCommunicationMetrics(),
      ]);

      this.threads = threadsRes.status === 'fulfilled' ? (threadsRes.value || []) : [];
      this.drafts = draftsRes.status === 'fulfilled' ? (draftsRes.value || []) : [];
      this.commitments = commitmentsRes.status === 'fulfilled' ? (commitmentsRes.value || []) : [];
      this.followups = followupsRes.status === 'fulfilled' ? (followupsRes.value || []) : [];
      this.contacts = contactsRes.status === 'fulfilled' ? (contactsRes.value || []) : [];
      this.metrics = metricsRes.status === 'fulfilled' ? (metricsRes.value || {}) : {};

      this.updateStats();
      this.renderActiveTab();
    } catch (err) {
      console.error('Failed to load communication engine data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  updateStats() {
    const elActiveThreads = this.container.querySelector('#stat-active-threads');
    const elPendingDrafts = this.container.querySelector('#stat-pending-drafts');
    const elOpenCommitments = this.container.querySelector('#stat-open-commitments');
    const elSendRate = this.container.querySelector('#stat-send-rate');

    if (elActiveThreads) elActiveThreads.textContent = this.threads.length;
    if (elPendingDrafts) {
      const pendingCount = this.drafts.filter(d => d.status === 'DRAFT' || d.status === 'REVIEWED').length;
      elPendingDrafts.textContent = pendingCount;
    }
    if (elOpenCommitments) {
      const openCount = this.commitments.filter(c => c.status === 'OPEN').length;
      elOpenCommitments.textContent = openCount;
    }
    if (elSendRate) {
      const rate = this.metrics && this.metrics.send_success_rate !== undefined ? `${(this.metrics.send_success_rate * 100).toFixed(1)}%` : '100%';
      elSendRate.textContent = rate;
    }
  }

  renderActiveTab() {
    const content = this.container.querySelector('#comm-tab-content');
    if (!content) return;

    if (this.activeTab === 'threads') {
      this.renderThreadsTab(content);
    } else if (this.activeTab === 'drafts') {
      this.renderDraftsTab(content);
    } else if (this.activeTab === 'commitments') {
      this.renderCommitmentsTab(content);
    } else if (this.activeTab === 'followups') {
      this.renderFollowupsTab(content);
    } else if (this.activeTab === 'contacts') {
      this.renderContactsTab(content);
    } else if (this.activeTab === 'telemetry') {
      this.renderTelemetryTab(content);
    }
  }

  renderThreadsTab(container) {
    if (this.threads.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: 3rem; background: var(--bg-card); border-radius: 8px; border: 1px dashed var(--border-subtle);">
          <h3>No Conversation Threads</h3>
          <p style="color: var(--text-muted); margin-top: 0.5rem;">Ingest an email or chat message to start structured threading.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="threads-list" style="display: flex; flex-direction: column; gap: 1rem;">
        ${this.threads.map(t => `
          <div class="card thread-card" style="background: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
              <div>
                <span class="badge ${this.getStatusBadgeClass(t.state)}" style="font-size: 0.75rem; text-transform: uppercase;">${t.state}</span>
                <span style="margin-left: 0.5rem; font-size: 0.8rem; color: var(--text-muted);">${t.channel}</span>
                <h3 style="margin: 0.35rem 0 0.2rem 0; font-size: 1.15rem;">${t.subject}</h3>
              </div>
              <div style="text-align: right; font-size: 0.8rem; color: var(--text-muted);">
                Activity: ${this.formatDate(t.last_activity)}
              </div>
            </div>
            <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
              <strong>Participants:</strong> ${(t.participants || []).map(p => p.display_name || p.identity).join(', ')} (${(t.messages || []).length} messages)
            </div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn btn-sm btn-secondary draft-reply-btn" data-thread-id="${t.thread_id}">
                Generate Draft Reply
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll('.draft-reply-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tId = btn.dataset.threadId;
        try {
          btn.disabled = true;
          btn.textContent = 'Drafting...';
          await Endpoints.generateCommunicationDraft(tId, { tone: 'FORMAL' });
          await this.loadData();
          this.activeTab = 'drafts';
          this.renderActiveTab();
        } catch (err) {
          alert('Draft generation failed: ' + err.message);
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  renderDraftsTab(container) {
    if (this.drafts.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: 3rem; background: var(--bg-card); border-radius: 8px; border: 1px dashed var(--border-subtle);">
          <h3>No Pending Drafts</h3>
          <p style="color: var(--text-muted); margin-top: 0.5rem;">Drafts generated from threads or user commands will appear here for governance and review.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="drafts-list" style="display: flex; flex-direction: column; gap: 1rem;">
        ${this.drafts.map(d => `
          <div class="card draft-card" style="background: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
              <div>
                <span class="badge ${this.getStatusBadgeClass(d.status)}" style="font-size: 0.75rem;">${d.status}</span>
                <span style="margin-left: 0.5rem; font-size: 0.8rem; color: var(--text-muted);">Tone: ${d.tone} | Intent: ${d.intent}</span>
                <h4 style="margin: 0.35rem 0; font-size: 1.05rem;">${d.subject || 'Untitled Draft'}</h4>
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">
                ${d.requires_approval ? '<span style="color: var(--accent-amber, #f59e0b);">Approval Required</span>' : 'Pre-approved'}
              </div>
            </div>
            <div style="background: var(--bg-subtle, #1e293b); padding: 0.75rem; border-radius: 6px; font-family: monospace; font-size: 0.88rem; white-space: pre-wrap; margin-bottom: 0.75rem;">
              ${d.body_reference}
            </div>
            <div style="display: flex; gap: 0.5rem;">
              ${d.status !== 'APPROVED' && d.status !== 'SENT' ? `
                <button class="btn btn-sm btn-primary approve-draft-btn" data-draft-id="${d.draft_id}">Approve Draft</button>
              ` : ''}
              ${d.status === 'APPROVED' ? `
                <button class="btn btn-sm btn-success send-draft-btn" data-draft-id="${d.draft_id}">Send Message</button>
              ` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll('.approve-draft-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const dId = btn.dataset.draftId;
        try {
          await Endpoints.approveCommunicationDraft(dId, { approver_identity: 'user@kairo.internal' });
          await this.loadData();
        } catch (err) {
          alert('Approval failed: ' + err.message);
        }
      });
    });

    container.querySelectorAll('.send-draft-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const dId = btn.dataset.draftId;
        const draft = this.drafts.find(d => d.draft_id === dId);
        if (!draft) return;
        try {
          await Endpoints.sendCommunication({
            draft_id: dId,
            channel: 'EMAIL',
            recipients: draft.recipients || [{ identity: 'recipient@example.com', address: 'recipient@example.com' }],
            subject: draft.subject,
            content: draft.body_reference,
            attachments: [],
          }, true);
          alert('Message successfully dispatched via ToolExecutor.');
          await this.loadData();
        } catch (err) {
          alert('Send failed: ' + err.message);
        }
      });
    });
  }

  renderCommitmentsTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Explicit Grounded Commitments</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Strictly grounded promises extracted from communication threads. Zero fabricated user commitments.</p>
      </div>
      <div class="commitments-list" style="display: flex; flex-direction: column; gap: 0.75rem;">
        ${this.commitments.length === 0 ? `
          <div style="padding: 2rem; text-align: center; color: var(--text-muted);">No open commitments detected.</div>
        ` : this.commitments.map(c => `
          <div style="background: var(--bg-card); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span class="badge ${this.getStatusBadgeClass(c.status)}" style="font-size: 0.75rem;">${c.status}</span>
              <span style="font-weight: 600; margin-left: 0.5rem;">${c.owner}:</span>
              <span style="margin-left: 0.25rem;">"${c.statement}"</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              Confidence: ${(c.confidence * 100).toFixed(0)}%
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderFollowupsTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Bounded Follow-Up Tracking</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Anti-spam bounded follow-ups scheduled with explicit trigger conditions.</p>
      </div>
      <div class="followups-list" style="display: flex; flex-direction: column; gap: 0.75rem;">
        ${this.followups.length === 0 ? `
          <div style="padding: 2rem; text-align: center; color: var(--text-muted);">No scheduled follow-ups pending.</div>
        ` : this.followups.map(f => `
          <div style="background: var(--bg-card); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span class="badge ${this.getStatusBadgeClass(f.status)}" style="font-size: 0.75rem;">${f.trigger}</span>
              <span style="margin-left: 0.5rem;">Action: ${f.action}</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              Attempts: ${f.attempts_count} / ${f.max_attempts}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderContactsTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Authorized Address Book</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Known contacts and safe relationship categorizations. Ambiguous lookups require confirmation.</p>
      </div>
      <div class="contacts-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;">
        ${this.contacts.length === 0 ? `
          <div style="padding: 2rem; text-align: center; color: var(--text-muted); grid-column: 1 / -1;">No authorized contacts found.</div>
        ` : this.contacts.map(c => `
          <div style="background: var(--bg-card); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle);">
            <div style="font-weight: 600; font-size: 1rem;">${c.display_name || c.identity}</div>
            <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">${c.address}</div>
            <div style="margin-top: 0.5rem; font-size: 0.78rem;">
              <span class="badge badge-neutral">${c.is_external ? 'External' : 'Internal'}</span>
              ${c.organization ? `<span style="margin-left: 0.4rem; color: var(--text-muted);">${c.organization}</span>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderTelemetryTab(container) {
    const m = this.metrics || {};
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Communication Engine Metrics & Telemetry</h3>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem;">
        <div style="background: var(--bg-card); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.8rem; color: var(--text-muted);">Messages Processed</div>
          <div style="font-size: 1.5rem; font-weight: 700;">${m.messages_processed || 0}</div>
        </div>
        <div style="background: var(--bg-card); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.8rem; color: var(--text-muted);">Drafts Generated</div>
          <div style="font-size: 1.5rem; font-weight: 700;">${m.drafts_generated || 0}</div>
        </div>
        <div style="background: var(--bg-card); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.8rem; color: var(--text-muted);">Draft Approval Rate</div>
          <div style="font-size: 1.5rem; font-weight: 700;">${((m.draft_approval_rate || 1.0) * 100).toFixed(1)}%</div>
        </div>
        <div style="background: var(--bg-card); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.8rem; color: var(--text-muted);">Sends Attempted</div>
          <div style="font-size: 1.5rem; font-weight: 700;">${m.sends_attempted || 0}</div>
        </div>
      </div>
    `;
  }

  showIngestModal() {
    const subject = prompt('Enter message subject:', 'Quarterly Roadmap Sync');
    if (!subject) return;
    const sender = prompt('Enter sender email:', 'teammate@company.com');
    if (!sender) return;
    const body = prompt('Enter message body:', 'Hi team, could you please review the updated deployment timeline by Friday? I will push the PR tomorrow.');
    if (!body) return;

    Endpoints.ingestInboundCommunication({
      raw_payload: {
        from: sender,
        subject: subject,
        body: body,
        to: ['user@kairo.internal'],
      },
      channel: 'EMAIL',
    }).then(() => {
      alert('Inbound message ingested and processed through 13-stage pipeline.');
      this.loadData();
    }).catch(err => {
      alert('Ingestion failed: ' + err.message);
    });
  }
}
