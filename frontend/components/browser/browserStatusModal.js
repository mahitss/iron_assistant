/**
 * Kairo Browser Action Status Modal
 * Displays current page and action status for automated web inspection without exposing credentials.
 */

export class BrowserStatusModal {
  constructor() {
    this.modalEl = null;
  }

  open({ url = 'https://docs.github.com/en/actions', status = 'Inspecting documentation and checking CI workflow syntax...' } = {}) {
    this.modalEl = document.createElement('div');
    this.modalEl.className = 'modal-backdrop';
    this.modalEl.innerHTML = `
      <div class="modal-card" role="dialog" aria-labelledby="browser-status-title">
        <div class="modal-header">
          <div class="browser-header-row">
            <span class="browser-icon">🌐</span>
            <h2 id="browser-status-title">Browser Session</h2>
          </div>
          <button class="modal-close-btn" aria-label="Close dialog">&times;</button>
        </div>
        <div class="browser-body">
          <div class="browser-address-bar">
            <span class="browser-protocol">https://</span>
            <input type="text" class="browser-url font-mono" readonly value="${escapeHtml(url)}" />
            <span class="badge badge-success">SANDBOX</span>
          </div>

          <div class="browser-preview-viewport">
            <div class="browser-viewport-overlay">
              <div class="loading-spinner"></div>
              <p class="browser-action-status">${escapeHtml(status)}</p>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(this.modalEl);

    const close = () => this.modalEl.remove();
    this.modalEl.querySelector('.modal-close-btn').addEventListener('click', close);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
