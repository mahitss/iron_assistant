/**
 * ApprovalBanner Component
 * Renders high-visibility human-in-the-loop approval cards with clear risk indicators.
 */

export class ApprovalBanner {
  constructor(props = {}) {
    this.props = props;
  }

  render() {
    return ApprovalBanner.render(this.props);
  }

  static render(appr) {
    if (!appr) return '';
    const risk = (appr.risk_level || 'HIGH').toUpperCase();
    const isCritical = risk === 'CRITICAL';
    const description = appr.description || appr.action_description || `Kairo is requesting permission to execute: ${appr.action || appr.tool_name || 'custom_action'}`;

    return `
      <div class="approval-card-wrapper ${isCritical ? 'critical' : 'warning'}" id="approval-${appr.id}">
        <div class="approval-card-header">
          <div class="approval-title-group">
            <span class="approval-lock-icon">🔐</span>
            <strong class="approval-title">APPROVAL REQUIRED</strong>
          </div>
          <span class="risk-pill ${isCritical ? 'risk-critical' : 'risk-high'}">${risk} RISK</span>
        </div>

        <div class="approval-card-body">
          <div class="approval-action-text">
            ${this._escapeHtml(description)}
          </div>

          <div class="approval-details-grid">
            <div class="detail-row">
              <span class="detail-name">Tool / Action:</span>
              <code class="detail-code">${this._escapeHtml(appr.tool_name || appr.action || 'custom_action')}</code>
            </div>
            ${appr.repository || appr.metadata?.repository ? `
              <div class="detail-row">
                <span class="detail-name">Repository:</span>
                <span class="detail-val">${this._escapeHtml(appr.repository || appr.metadata?.repository)}</span>
              </div>
            ` : ''}
            ${appr.branch || appr.metadata?.branch ? `
              <div class="detail-row">
                <span class="detail-name">Branch:</span>
                <span class="detail-val">${this._escapeHtml(appr.branch || appr.metadata?.branch)}</span>
              </div>
            ` : ''}
          </div>
        </div>

        <div class="approval-card-actions">
          <button class="btn-deny" onclick="window.kairoApp ? window.kairoApp.decideApproval('${appr.id}', 'deny') : null" aria-label="Deny requested action">
            DENY
          </button>
          <button class="btn-approve" onclick="window.kairoApp ? window.kairoApp.decideApproval('${appr.id}', 'approve') : null" aria-label="Approve requested action">
            APPROVE ACTION
          </button>
        </div>
      </div>
    `;
  }

  static _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
