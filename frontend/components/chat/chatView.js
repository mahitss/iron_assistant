/**
 * ChatView — Primary Kairo Conversational Interface
 * Renders conversation history, streaming tokens, tool activity pills,
 * multi-agent progress trackers, context chips, and inline approvals.
 */

import { store } from '../../state/store.js';

export class ChatView {
  constructor(options = {}) {
    this.store = options.store || store;
  }

  render() {
    const state = this.store.getState();
    const conversations = state.conversations || [];
    const isStreaming = state.isStreaming;
    const activeProject = state.activeProject;
    const contextPacket = state.contextPacket;

    // Build lightweight context indicator chip
    let contextChipText = '';
    if (activeProject) {
      const repo = activeProject.repositories && activeProject.repositories.length > 0 ? activeProject.repositories[0] : null;
      contextChipText = `${this._escapeHtml(activeProject.name)}${repo ? ` &bull; ${this._escapeHtml(repo)}` : ''}`;
      if (contextPacket && contextPacket.total_items) {
        contextChipText += ` &bull; ${contextPacket.total_items} context item(s)`;
      }
    } else {
      contextChipText = 'Global Session &bull; Task-oriented context';
    }

    return `
      <div class="chat-view-container">
        <!-- Top Chat Header with Lightweight Context Indicator -->
        <div class="chat-header-bar">
          <div class="chat-header-left">
            <h2 class="chat-title">Conversation</h2>
            <button class="context-indicator-chip" onclick="window.kairoApp.openContextInspector()" title="Click to inspect why context was selected" aria-label="Context Inspector">
              <span class="chip-icon">🧠</span>
              <span class="chip-text">${contextChipText}</span>
              <span class="chip-action">[Context]</span>
            </button>
          </div>

          <div class="chat-header-actions">
            <button class="btn-sm btn-outline" onclick="window.kairoApp.newChat()" title="Start a fresh conversation (Ctrl+N)">
              <span class="btn-icon">✨</span>
              <span>New Chat</span>
            </button>
          </div>
        </div>

        <!-- Scrollable Messages Feed -->
        <div class="chat-feed-scroll" id="chatFeed" role="log" aria-live="polite">
          ${conversations.length === 0 ? `
            <div class="chat-welcome-hero">
              <div class="welcome-orb">K</div>
              <h3 class="welcome-title">How can Kairo assist you today?</h3>
              <p class="welcome-subtitle">Ask questions about your projects, trigger research, run workflows, or inspect code repositories.</p>

              <div class="welcome-grid">
                <button class="welcome-card" onclick="window.kairoApp.sendMessageFromInput('Check why the build is failing')">
                  <div class="welcome-card-title">🔍 Check CI Build</div>
                  <div class="welcome-card-desc">Inspect recent workflows and repository status.</div>
                </button>
                <button class="welcome-card" onclick="window.kairoApp.sendMessageFromInput('What should I work on today?')">
                  <div class="welcome-card-title">📋 Daily Priorities</div>
                  <div class="welcome-card-desc">Review active projects, pending approvals, and goals.</div>
                </button>
                <button class="welcome-card" onclick="window.kairoApp.sendMessageFromInput('Continue research from yesterday')">
                  <div class="welcome-card-title">🧠 Retrieve Context</div>
                  <div class="welcome-card-desc">Pick up where you left off using scoped memory.</div>
                </button>
              </div>
            </div>
          ` : conversations.map((msg, index) => this._renderMessageItem(msg, index, isStreaming && index === conversations.length - 1)).join('')}

          ${isStreaming && conversations[conversations.length - 1]?.role !== 'assistant' ? `
            <div class="message-wrapper assistant">
              <div class="message-avatar">K</div>
              <div class="message-bubble assistant">
                <div class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          ` : ''}
        </div>

        <!-- Chat Composer Bar -->
        <div class="chat-composer-container" id="chatComposerMount">
          <!-- Injected by Composer component -->
        </div>
      </div>
    `;
  }

  _renderMessageItem(msg, index, isCurrentlyStreaming = false) {
    const isUser = msg.role === 'user';

    return `
      <div class="message-wrapper ${isUser ? 'user' : 'assistant'}" data-index="${index}">
        <div class="message-avatar">${isUser ? 'U' : 'K'}</div>
        <div class="message-content-col">
          <!-- Tool Activity Pills (Compact with expandable details) -->
          ${msg.toolActivities && msg.toolActivities.length > 0 ? this._renderToolActivities(msg.toolActivities) : ''}

          <!-- Multi-Agent Progress Tracker (Safe high-level milestones without CoT) -->
          ${msg.agentProgress && msg.agentProgress.length > 0 ? this._renderAgentProgress(msg.agentProgress) : ''}

          <!-- Inline Approval Banner if turn requested human approval -->
          ${msg.approvalRequest ? this._renderInlineApproval(msg.approvalRequest) : ''}

          <!-- Message Text Bubble -->
          <div class="message-bubble ${isUser ? 'user' : 'assistant'}">
            <div class="message-text">${this._formatMarkdown(msg.content)}</div>
            ${isCurrentlyStreaming ? '<span class="streaming-cursor"></span>' : ''}
          </div>
          <div class="message-timestamp">${this._formatTimestamp(msg.timestamp)}</div>
        </div>
      </div>
    `;
  }

  _renderToolActivities(activities = []) {
    return `
      <div class="tool-activity-accordion">
        <details class="tool-details">
          <summary class="tool-summary">
            <span class="tool-summary-icon">⚙️</span>
            <span>Tools Executed (${activities.length})</span>
            <span class="tool-summary-pills">
              ${activities.map(a => `<span class="tool-badge ${a.status === 'success' ? 'success' : 'failed'}">✓ ${this._escapeHtml(a.tool || a.name || 'tool')}</span>`).join('')}
            </span>
          </summary>
          <div class="tool-accordion-content">
            ${activities.map(a => `
              <div class="tool-run-row">
                <div class="tool-run-header">
                  <strong>${this._escapeHtml(a.tool || a.name)}</strong>
                  <span class="status-pill status-${a.status === 'success' ? 'active' : 'danger'}">${a.status || 'done'}</span>
                </div>
                ${a.summary ? `<div class="tool-run-summary">${this._escapeHtml(a.summary)}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </details>
      </div>
    `;
  }

  _renderAgentProgress(agentSteps = []) {
    return `
      <div class="agent-progress-box">
        <div class="agent-box-title">
          <span class="agent-pulse-icon">●</span>
          <span>Multi-Agent Workflow Progress</span>
        </div>
        <div class="agent-steps-list">
          ${agentSteps.map(step => `
            <div class="agent-step-item ${step.status === 'running' ? 'running' : 'completed'}">
              <span class="agent-step-status">${step.status === 'running' ? '●' : '✓'}</span>
              <span class="agent-specialist">${this._escapeHtml(step.specialist || step.agent)}:</span>
              <span class="agent-step-desc">${this._escapeHtml(step.description || step.action)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderInlineApproval(appr) {
    return `
      <div class="in-chat-approval-banner">
        <div class="approval-banner-header">
          <span class="approval-icon">🔐</span>
          <span class="approval-heading">HUMAN APPROVAL REQUIRED</span>
          <span class="badge badge-${appr.risk_level === 'CRITICAL' ? 'danger' : 'warning'}">${appr.risk_level || 'HIGH'} RISK</span>
        </div>
        <div class="approval-banner-desc">
          ${this._escapeHtml(appr.action_description || `Kairo wants to execute action: ${appr.tool_name}`)}
        </div>
        <div class="approval-banner-meta">
          <span>Target Tool: <code>${this._escapeHtml(appr.tool_name)}</code></span>
          ${appr.repository ? `<span>Repository: <strong>${this._escapeHtml(appr.repository)}</strong></span>` : ''}
        </div>
        <div class="approval-banner-actions">
          <button class="btn-sm btn-outline danger" onclick="window.kairoApp.decideApproval('${appr.id}', 'deny')">DENY</button>
          <button class="btn-sm btn-primary" onclick="window.kairoApp.decideApproval('${appr.id}', 'approve')">APPROVE ACTION</button>
        </div>
      </div>
    `;
  }

  _formatMarkdown(text) {
    if (!text) return '';
    // Safe text formatting (sanitizes HTML characters and formats basic markdown)
    const escaped = this._escapeHtml(text);
    return escaped
      .replace(/\n\n/g, '<br/><br/>')
      .replace(/\n/g, '<br/>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  _formatTimestamp(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
