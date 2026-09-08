/**
 * ProjectsView Component — Workspaces, Repositories & Project Context
 */

import { store } from '../../state/store.js';

export class ProjectsView {
  constructor(options = {}) {
    this.store = options.store || store;
    this.isCreating = false;
  }

  render() {
    const state = this.store.getState();
    const projects = state.projects || [];
    const activeProject = state.activeProject;

    return `
      <div class="projects-view-container">
        <div class="view-header">
          <div class="header-titles">
            <h1 class="view-title">Projects & Workspaces</h1>
            <p class="view-subtitle">Manage project boundaries, repository anchors, and associated workflows.</p>
          </div>
          <button class="btn-primary" onclick="window.kairoApp.toggleCreateProjectForm()">
            + New Project
          </button>
        </div>

        ${this.isCreating ? `
          <div class="card create-project-card">
            <div class="card-title">Create Project Workspace</div>
            <form onsubmit="window.kairoApp.handleCreateProject(event)" class="create-project-form">
              <div class="form-group">
                <label class="form-label" for="newProjectName">Project Name *</label>
                <input type="text" id="newProjectName" class="form-input" placeholder="e.g. Kairo Core, DataPipeline, Portfolio" required />
              </div>
              <div class="form-group">
                <label class="form-label" for="newProjectDesc">Description</label>
                <input type="text" id="newProjectDesc" class="form-input" placeholder="Brief explanation of the project goals" />
              </div>
              <div class="form-actions">
                <button type="button" class="btn-outline" onclick="window.kairoApp.toggleCreateProjectForm()">Cancel</button>
                <button type="submit" class="btn-primary">Create Workspace</button>
              </div>
            </form>
          </div>
        ` : ''}

        <div class="grid-2">
          <!-- Projects List -->
          <div class="card">
            <div class="card-title">
              <span>📚</span>
              <span>YOUR WORKSPACES (${projects.length})</span>
            </div>
            <p class="card-subtitle">Click to switch your active working context.</p>

            <div class="projects-cards-list">
              ${projects.length === 0 ? `
                <div class="empty-state-box">
                  <span class="empty-icon">📁</span>
                  <div>No projects found. Create your first workspace to anchor context.</div>
                </div>
              ` : projects.map(p => {
                const isActive = activeProject && activeProject.id === p.id;
                return `
                  <div class="project-workspace-card ${isActive ? 'active' : ''}" onclick="window.kairoApp.switchActiveProject('${p.id}')">
                    <div class="card-top-row">
                      <div class="project-card-name">${this._escapeHtml(p.name)}</div>
                      <span class="status-pill status-${p.status.toLowerCase()}">${p.status}</span>
                    </div>
                    <div class="project-card-desc">${this._escapeHtml(p.description || 'Workspace project')}</div>
                    <div class="project-card-footer">
                      <span>${p.repositories ? p.repositories.length : 0} repo(s)</span>
                      <span>${p.workflows ? p.workflows.length : 0} workflow(s)</span>
                      ${isActive ? '<span class="badge badge-success">ACTIVE CONTEXT</span>' : '<button class="btn-text">Select &rarr;</button>'}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Active Project Workspace Details -->
          <div class="card">
            <div class="card-title">
              <span>⚙️</span>
              <span>WORKSPACE DETAILS</span>
            </div>
            <p class="card-subtitle">Context anchors and linked resources for the active project.</p>

            ${activeProject ? `
              <div class="active-project-detail-panel">
                <div class="detail-header-card">
                  <div class="detail-title-row">
                    <h3 class="detail-name">${this._escapeHtml(activeProject.name)}</h3>
                    <button class="btn-sm btn-outline danger" onclick="window.kairoApp.deleteProject('${activeProject.id}')">Delete Project</button>
                  </div>
                  <p class="detail-desc-text">${this._escapeHtml(activeProject.description || 'Autonomous assistant workspace')}</p>
                </div>

                <!-- Linked Repositories -->
                <div class="resource-block">
                  <div class="resource-block-header">
                    <strong>Linked Repositories</strong>
                    <button class="btn-text" onclick="window.kairoApp.promptLinkRepository('${activeProject.id}')">+ Link Repo</button>
                  </div>
                  ${activeProject.repositories && activeProject.repositories.length > 0 ? activeProject.repositories.map(r => `
                    <div class="resource-row">
                      <span class="resource-icon">📦</span>
                      <code class="resource-code">${this._escapeHtml(r)}</code>
                      <span class="badge badge-default">Git Anchor</span>
                    </div>
                  `).join('') : '<div class="resource-empty">No repositories linked yet.</div>'}
                </div>

                <!-- Action Shortcut to Chat -->
                <div style="margin-top: 1.5rem;">
                  <button class="btn-primary" style="width: 100%; justify-content: center;" onclick="window.kairoApp.navigateTo('chat')">
                    Open Chat with ${this._escapeHtml(activeProject.name)} Context &rarr;
                  </button>
                </div>
              </div>
            ` : `
              <div class="empty-state-box">
                <div>Select a project from the left or create a new one to view linked repositories and workflows.</div>
              </div>
            `}
          </div>
        </div>
      </div>
    `;
  }

  toggleCreate() {
    this.isCreating = !this.isCreating;
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
