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
    const activeTask = state.activeTask;
    const contextPacket = state.contextPacket;

    // Build lightweight context indicator chip (Spec 129: Project & Task context indicator)
    let contextChipText = '';
    if (activeProject) {
      const repo = activeProject.repositories && activeProject.repositories.length > 0 ? activeProject.repositories[0] : null;
      contextChipText = `Project: ${this._escapeHtml(activeProject.name)}${repo ? ` &bull; ${this._escapeHtml(repo)}` : ''}`;
      if (activeTask) {
        contextChipText += ` &bull; Task: ${this._escapeHtml(activeTask.title || activeTask.id || 'Active')}`;
      }
      if (contextPacket && contextPacket.total_items) {
        contextChipText += ` &bull; ${contextPacket.total_items} item(s)`;
      }
    } else if (activeTask) {
      contextChipText = `Task: ${this._escapeHtml(activeTask.title || activeTask.id)} &bull; Global Session`;
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
          <!-- Skill Indicator Pill & Bounded Execution Steps -->
          ${msg.skill ? this._renderSkillActivity(msg.skill) : ''}

          <!-- Tool Activity Pills (Compact with expandable details) -->
          ${msg.toolActivities && msg.toolActivities.length > 0 ? this._renderToolActivities(msg.toolActivities) : ''}

          <!-- Multi-Agent Progress Tracker (Safe high-level milestones without CoT) -->
          ${msg.agentProgress && msg.agentProgress.length > 0 ? this._renderAgentProgress(msg.agentProgress) : ''}

          <!-- Inline Approval Banner if turn requested human approval -->
          ${msg.approvalRequest ? this._renderInlineApproval(msg.approvalRequest) : ''}

          <!-- Clarification Option Card (Task 35, Spec 45, 46, 126) -->
          ${msg.clarification ? this._renderClarificationCard(msg.clarification) : ''}

          <!-- Intent Preview Banner (Task 35, Spec 127) -->
          ${msg.intentPreview ? this._renderIntentPreview(msg.intentPreview) : ''}

          <!-- Multimodal Attachment Tag (User message) -->
          ${isUser && msg.attachment ? `
            <div class="user-attachment-pill" style="display: inline-flex; align-items: center; gap: 0.35rem; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 6px; padding: 0.2rem 0.5rem; font-size: 0.75rem; margin-bottom: 0.3rem; color: #38bdf8;">
              <span>${msg.attachment.type === 'document' ? '📄' : (msg.attachment.type === 'audio' ? '🎙️' : '🖼️')}</span>
              <strong>${this._escapeHtml(msg.attachment.name || 'Attachment')}</strong>
            </div>
          ` : ''}

          <!-- Screen Sharing Indicator -->
          ${isUser && msg.screenContext ? `
            <div class="user-screen-pill" style="display: inline-flex; align-items: center; gap: 0.35rem; background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; padding: 0.2rem 0.5rem; font-size: 0.75rem; margin-bottom: 0.3rem; color: #f59e0b;">
              <span>🖥️</span>
              <span>Screen Context: <strong>${this._escapeHtml(msg.screenContext.device_id || 'Companion')}</strong></span>
            </div>
          ` : ''}

          <!-- Message Text Bubble -->
          <div class="message-bubble ${isUser ? 'user' : 'assistant'}">
            <!-- Uncertainty Warning Banner (Spec 63) -->
            ${!isUser && msg.uncertainty_note ? `
              <div class="uncertainty-callout" style="display: flex; align-items: center; gap: 0.4rem; background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; padding: 0.35rem 0.6rem; border-radius: 4px; margin-bottom: 0.5rem; font-size: 0.8rem; color: #fbbf24;">
                <span>⚠️</span>
                <span>${this._escapeHtml(msg.uncertainty_note)}</span>
              </div>
            ` : ''}

            <div class="message-text">${this._formatMarkdown(msg.content)}</div>
            ${isCurrentlyStreaming ? '<span class="streaming-cursor"></span>' : ''}

            <!-- Grounded Citations & Evidence Block (Specs 61, 85-89) -->
            ${!isUser && ((msg.citations && msg.citations.length > 0) || (msg.evidence && msg.evidence.length > 0)) ? `
              <div class="multimodal-evidence-footer" style="margin-top: 0.6rem; padding-top: 0.5rem; border-top: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.78rem;">
                ${msg.citations && msg.citations.length > 0 ? `
                  <div style="display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;">
                    <strong style="color: var(--text-muted);">Sources:</strong>
                    ${msg.citations.map(c => `
                      <span style="background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 4px; padding: 0.1rem 0.4rem; color: #38bdf8;">
                        ${this._escapeHtml(c)}
                      </span>
                    `).join('')}
                  </div>
                ` : ''}
              </div>
            ` : ''}
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.2rem;">
            <div class="message-timestamp">${this._formatTimestamp(msg.timestamp)}</div>
            ${!isUser && !isCurrentlyStreaming ? this._renderFeedbackRow(msg, index) : ''}
          </div>
        </div>
      </div>
    `;
  }

  _renderFeedbackRow(msg, index) {
    const msgId = msg.id || `msg-${index}`;
    return `
      <div class="message-feedback-row" id="fb-row-${msgId}" style="display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.75rem;">
        <button class="btn-icon-subtle" onclick="window.kairoApp?.rateMessage?.('${msgId}', 'POSITIVE')" title="Helpful response (👍)" style="background: none; border: none; cursor: pointer; opacity: 0.65; hover: opacity: 1;">👍</button>
        <button class="btn-icon-subtle" onclick="window.kairoApp?.promptNegativeFeedback?.('${msgId}')" title="Not helpful (👎)" style="background: none; border: none; cursor: pointer; opacity: 0.65; hover: opacity: 1;">👎</button>
        <button class="btn-link-subtle" onclick="window.kairoApp?.promptCorrection?.('${msgId}')" title="Correct Kairo for this project" style="background: none; border: none; cursor: pointer; color: var(--text-muted); font-size: 0.72rem; text-decoration: underline;">✏️ Correct</button>
      </div>
    `;
  }

  _renderSkillActivity(skill) {
    const skillName = typeof skill === 'string' ? skill : (skill.name || skill.id || 'Skill');
    const state = (skill.state || 'RUNNING').toUpperCase();
    const isCompleted = state === 'COMPLETED';
    const isFailed = state === 'FAILED' || state === 'TIMED_OUT';
    const stateClass = isCompleted ? 'badge-success' : (isFailed ? 'badge-danger' : 'badge-primary');
    const steps = Array.isArray(skill.steps) ? skill.steps : [];

    return `
      <div class="skill-activity-container" style="margin-bottom: 0.5rem;">
        <div class="skill-activity-header" style="display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 9999px; padding: 0.25rem 0.75rem; font-size: 0.8rem;">
          <span style="color: #38bdf8;">⚡</span>
          <span style="color: var(--text-muted);">Using:</span>
          <strong style="color: var(--text-main);">${this._escapeHtml(skillName)}</strong>
          <span class="badge ${stateClass}" style="font-size: 0.68rem; padding: 0.1rem 0.4rem;">
            ${isCompleted ? '✓' : (isFailed ? '✕' : '●')} ${this._escapeHtml(state)}
          </span>
        </div>
        ${steps.length > 0 ? `
          <div class="skill-steps-list" style="margin-top: 0.35rem; padding-left: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">
            ${steps.map(step => `
              <div class="skill-step-item" style="display: flex; align-items: center; gap: 0.35rem; margin-top: 0.15rem;">
                <span style="color: ${step.completed ? '#10b981' : '#38bdf8'}; font-weight: bold;">
                  ${step.completed ? '✓' : '●'}
                </span>
                <span>${this._escapeHtml(step.title || step.step || step.tool || '')}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}
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

  _renderClarificationCard(clarification) {
    const options = clarification.options || [];
    return `
      <div class="clarification-card" style="margin-bottom: 0.75rem; padding: 0.75rem 1rem; background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px;">
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; font-size: 0.85rem; font-weight: 600; color: #818cf8;">
          <span>🤔</span>
          <span>${this._escapeHtml(clarification.reason || 'Clarification Needed')}</span>
        </div>
        ${options.length > 0 ? `
          <div class="clarification-options" style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.4rem;">
            ${options.map(opt => `
              <button
                type="button"
                class="btn-sm btn-outline clarification-btn"
                onclick="window.kairoApp?.handleClarificationOption?.('${this._escapeHtml(opt.value || opt.label)}')"
                style="background: rgba(99, 102, 241, 0.15); border-color: #6366f1; color: #c7d2fe; cursor: pointer; border-radius: 4px; padding: 0.25rem 0.6rem;"
              >
                ${this._escapeHtml(opt.label || opt.value)}
              </button>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  _renderIntentPreview(preview) {
    const isRisky = preview.risk === 'HIGH' || preview.risk === 'CRITICAL';
    return `
      <div class="intent-preview-banner" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.75rem; background: ${isRisky ? 'rgba(239, 68, 68, 0.1)' : 'rgba(56, 189, 248, 0.1)'}; border-left: 3px solid ${isRisky ? '#ef4444' : '#38bdf8'}; border-radius: 4px; margin-bottom: 0.5rem; font-size: 0.82rem; color: ${isRisky ? '#f87171' : '#38bdf8'};">
        <span>${isRisky ? '🛡️' : '🎯'}</span>
        <span><strong>Intent:</strong> ${this._escapeHtml(preview.text || preview.objective || '')}</span>
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
