/**
 * Kairo Computer Control Safety Modal
 * Clearly communicates: OFF, READY, ACTIVE, STOPPED.
 * Never silently enables computer control. Strict user confirmation required.
 */

import { store } from '../../state/store.js';

export class ComputerControlModal {
  constructor() {
    this.modalEl = null;
  }

  open() {
    const isStopped = store.isEmergencyStopped();
    const isEnabled = store.getState().capabilities?.['computer_control'] === true;
    const status = isStopped ? 'STOPPED' : isEnabled ? 'ACTIVE' : 'OFF';

    this.modalEl = document.createElement('div');
    this.modalEl.className = 'modal-backdrop';
    this.modalEl.innerHTML = `
      <div class="modal-card" role="dialog" aria-labelledby="cc-modal-title">
        <div class="modal-header">
          <h2 id="cc-modal-title">Computer Control Status</h2>
          <button class="modal-close-btn" aria-label="Close dialog">&times;</button>
        </div>
        <div class="modal-body">
          <div class="cc-status-banner cc-status-${status.toLowerCase()}">
            <span class="cc-status-indicator"></span>
            <div>
              <div class="cc-status-label">CURRENT STATUS</div>
              <strong class="cc-status-val">${status}</strong>
            </div>
          </div>

          <div class="cc-warning-box">
            <p><strong>Safety Boundaries:</strong> Computer control permits Kairo to simulate mouse navigation and keyboard input only within designated sandbox windows. Human-in-the-loop approvals are required for destructive operations.</p>
          </div>

          <div class="cc-options">
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Enable Controlled Interaction</strong>
                <p>Arm interaction for sandbox window only.</p>
              </div>
              <button class="btn ${isEnabled ? 'btn-secondary' : 'btn-primary'}" id="toggle-cc-btn" ${isStopped ? 'disabled' : ''}>
                ${isEnabled ? 'Disable Interaction' : 'Enable Interaction'}
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(this.modalEl);

    const close = () => this.modalEl.remove();
    this.modalEl.querySelector('.modal-close-btn').addEventListener('click', close);

    const toggleBtn = this.modalEl.querySelector('#toggle-cc-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        store.setCapability('computer_control', !isEnabled);
        close();
      });
    }
  }
}
