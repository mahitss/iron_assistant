/**
 * Kairo Command Center Application Entry Point
 * Orchestrates navigation, state synchronization, background probes, and modal interactions.
 */

import { store } from '../state/store.js';
import { Endpoints } from '../lib/api/endpoints.js';
import { shortcuts } from '../lib/shortcuts.js';
import { AppShell } from '../components/layout/shell.js';
import { CommandPalette } from '../components/layout/commandPalette.js';
import { HomeView } from '../components/home/homeView.js';
import { ChatView } from '../components/chat/chatView.js';
import { ProjectsView } from '../components/projects/projectsView.js';
import { AutomationsView } from '../components/automations/automationsView.js';
import { ActivityView } from '../components/activity/activityView.js';
import { SecurityView } from '../components/security/securityView.js';
import { MemoryView } from '../components/memory/memoryView.js';
import { NotificationsView } from '../components/notifications/notificationsView.js';
import { StatusView } from '../components/status/statusView.js';
import { SettingsView } from '../components/settings/settingsView.js';
import { KnowledgeView } from '../components/knowledge/knowledgeView.js';
import { EvaluationView } from '../components/evaluation/evaluationView.js';
import { TasksView } from '../components/tasks/tasksView.js';
import { EnvironmentView } from '../components/environment/environmentView.js';
import { VoiceModal } from '../components/voice/voiceModal.js';
import { ContextInspector } from '../components/context/contextInspector.js';
import { ComputerControlModal } from '../components/security/computerControlModal.js';
import { BrowserStatusModal } from '../components/browser/browserStatusModal.js';

export class KairoApp {
  constructor(rootContainer) {
    this.root = rootContainer;
    this.shell = null;
    this.palette = null;
    this.voiceModal = null;
    this.contextInspector = null;
    this.currentViewInstance = null;
  }

  async init() {
    // 1. Mount App Shell structure
    this.shell = new AppShell(this.root);
    this.shell.render();

    // 2. Initialize Modals
    this.palette = new CommandPalette();
    this.voiceModal = new VoiceModal();
    this.contextInspector = new ContextInspector();

    // 3. Register Global Keyboard Shortcuts
    shortcuts.register('open_palette', { key: 'k', ctrl: true, meta: true }, () => {
      this.palette.open();
    });

    shortcuts.register('new_chat', { key: 'n', ctrl: true, meta: true }, () => {
      this.navigateTo('chat');
      if (this.currentViewInstance instanceof ChatView) {
        this.currentViewInstance.startNewConversation();
      }
    });

    shortcuts.register('emergency_stop', { key: 'e', ctrl: true, shift: true }, () => {
      this.handleEmergencyStop();
    });

    // 4. Subscribe to Store changes
    store.subscribe((state, prev) => {
      if (state.currentView !== prev.currentView) {
        this.renderActiveView(state.currentView);
      }
      if (state.activeProject !== prev.activeProject) {
        this.refreshProjectContext(state.activeProject);
      }
    });

    // 5. Wire AppShell Topbar & Navigation Events
    this._wireShellEvents();

    // 6. Perform Initial Hydration
    await this.hydrateState();

    // 7. Render Initial View (default 'home')
    await this.renderActiveView(store.getState().currentView || 'home');
  }

  _wireShellEvents() {
    // Navigation item clicks
    const mainContent = this.root.querySelector('#main-content-viewport');
    
    // Project switcher
    const projectSelect = this.root.querySelector('#project-switcher-select');
    if (projectSelect) {
      projectSelect.addEventListener('change', (e) => {
        store.setActiveProject(e.target.value);
      });
    }

    // Emergency Stop button in topbar
    const stopBtn = this.root.querySelector('#emergency-stop-btn');
    if (stopBtn) {
      stopBtn.addEventListener('click', () => this.handleEmergencyStop());
    }

    // Global Search button
    const searchTrigger = this.root.querySelector('#global-search-trigger');
    if (searchTrigger) {
      searchTrigger.addEventListener('click', () => this.palette.open());
    }

    // Notifications bell
    const notifBtn = this.root.querySelector('#notifications-bell-btn');
    if (notifBtn) {
      notifBtn.addEventListener('click', () => this.navigateTo('notifications'));
    }

    // Navigation links in sidebar
    this.root.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetView = btn.dataset.view;
        if (targetView) this.navigateTo(targetView);
      });
    });
  }

  navigateTo(viewName) {
    store.setView(viewName);
    this.root.querySelectorAll('.nav-item').forEach(btn => {
      if (btn.dataset.view === viewName) {
        btn.classList.add('active');
        btn.setAttribute('aria-current', 'page');
      } else {
        btn.classList.remove('active');
        btn.removeAttribute('aria-current');
      }
    });
  }

  async renderActiveView(viewName) {
    const viewport = this.root.querySelector('#main-content-viewport');
    if (!viewport) return;

    viewport.innerHTML = '<div class="loading-spinner">Loading view...</div>';

    switch (viewName) {
      case 'home':
        this.currentViewInstance = new HomeView(viewport);
        break;
      case 'chat':
        this.currentViewInstance = new ChatView(viewport);
        break;
      case 'projects':
        this.currentViewInstance = new ProjectsView(viewport);
        break;
      case 'automations':
        this.currentViewInstance = new AutomationsView(viewport);
        break;
      case 'tasks':
        this.currentViewInstance = new TasksView(viewport);
        break;
      case 'activity':
        this.currentViewInstance = new ActivityView(viewport);
        break;
      case 'security':
        this.currentViewInstance = new SecurityView(viewport);
        break;
      case 'memory':
        this.currentViewInstance = new MemoryView(viewport);
        break;
      case 'notifications':
        this.currentViewInstance = new NotificationsView(viewport);
        break;
      case 'status':
        this.currentViewInstance = new StatusView(viewport);
        break;
      case 'settings':
        this.currentViewInstance = new SettingsView(viewport);
        break;
      case 'knowledge':
        this.currentViewInstance = new KnowledgeView(viewport);
        break;
      case 'environment':
        this.currentViewInstance = new EnvironmentView({ container: viewport, api: Endpoints });
        break;
      case 'evaluation':
        this.currentViewInstance = new EvaluationView({ container: viewport });
        await this.currentViewInstance.init();
        return;
      default:
        this.currentViewInstance = new HomeView(viewport);
    }

    await this.currentViewInstance.render();
  }

  async hydrateState() {
    try {
      // 1. Projects
      const projects = await Endpoints.listProjects();
      if (Array.isArray(projects) && projects.length > 0) {
        store.setProjects(projects);
        this.shell.updateProjectsDropdown(projects);
      }
    } catch (e) {
      console.warn('Could not load projects:', e);
    }

    try {
      // 2. Active Context
      const ctx = await Endpoints.getCurrentContext();
      if (ctx) store.setContext(ctx);
    } catch (e) {
      console.warn('Could not load current context:', e);
    }

    try {
      // 3. Pending Approvals
      const pending = await Endpoints.listPendingApprovals();
      const approvalsList = Array.isArray(pending) ? pending : (pending?.approvals || []);
      store.setApprovals(approvalsList);
    } catch (e) {
      console.warn('Could not load approvals:', e);
    }

    try {
      // 4. Notifications count
      const notifs = await Endpoints.listNotifications(true);
      const unread = notifs?.unread_count ?? (Array.isArray(notifs) ? notifs.length : 0);
      store.setUnreadNotificationsCount(unread);
    } catch (e) {
      console.warn('Could not load notifications:', e);
    }

    try {
      // 5. Emergency Stop status
      const estop = await Endpoints.getEmergencyStopStatus();
      if (estop?.is_stopped || estop?.emergency_stop_active) {
        store.setEmergencyStop(true, estop.reason || 'Active emergency stop');
      }
    } catch (e) {
      console.warn('Could not check emergency stop:', e);
    }
  }

  async refreshProjectContext(projectName) {
    try {
      const ctx = await Endpoints.getCurrentContext();
      if (ctx) store.setContext(ctx);
    } catch (err) {
      console.warn('Failed to refresh project context:', err);
    }
  }

  async handleEmergencyStop() {
    const isStopped = store.isEmergencyStopped();
    if (isStopped) {
      // Confirmation to resume/reset
      if (confirm('Emergency Stop is currently ACTIVE. Reset Emergency Stop and resume assistant capabilities?')) {
        try {
          await Endpoints.resetEmergencyStop();
          store.setEmergencyStop(false, null);
          alert('Emergency Stop reset. Kairo capabilities resumed.');
        } catch (err) {
          alert(`Failed to reset Emergency Stop: ${err.message}`);
        }
      }
    } else {
      // Trigger stop
      if (confirm('EMERGENCY STOP: Immediately halt all running tools, background agents, and computer controls?')) {
        try {
          await Endpoints.triggerEmergencyStop('Initiated via Unified Command Center topbar');
          store.setEmergencyStop(true, 'Initiated via Unified Command Center topbar');
          alert('STOPPED: All assistant operations have been halted immediately.');
        } catch (err) {
          alert(`Emergency stop failed: ${err.message}`);
        }
      }
    }
  }

  openVoiceModal(onSend) {
    this.voiceModal.open({ onSend });
  }

  openContextInspector() {
    this.contextInspector.open();
  }

  openComputerControlModal() {
    new ComputerControlModal().open();
  }

  openBrowserModal(details) {
    new BrowserStatusModal().open(details);
  }

  async rateMessage(messageId, feedbackType) {
    try {
      await Endpoints.submitFeedback({
        feedback_type: feedbackType,
        message_id: messageId,
        rating: feedbackType === 'POSITIVE' ? 5 : 1,
      });
      const el = document.getElementById(`fb-row-${messageId}`);
      if (el) el.innerHTML = `<span style="color: #10b981; font-size: 0.75rem;">✓ Feedback saved</span>`;
    } catch (e) {
      console.warn('Feedback submission error:', e);
    }
  }

  async promptNegativeFeedback(messageId) {
    const comment = prompt('What went wrong? (Optional details to help evaluate response):');
    if (comment === null) return;
    try {
      await Endpoints.submitFeedback({
        feedback_type: 'NEGATIVE',
        message_id: messageId,
        rating: 1,
        comment: comment || 'User flagged response as unhelpful',
      });
      const el = document.getElementById(`fb-row-${messageId}`);
      if (el) el.innerHTML = `<span style="color: #f59e0b; font-size: 0.75rem;">✓ Feedback recorded</span>`;
    } catch (e) {
      alert('Failed to record feedback: ' + e.message);
    }
  }

  async promptCorrection(messageId) {
    const correction = prompt('What is the correct behavior or setting? (e.g. "We use SQLite for this project"):');
    if (!correction) return;
    const activeProject = store.getState().activeProject;
    const scopeConfirm = confirm(`Save correction for current project (${activeProject ? (activeProject.name || activeProject.id || activeProject) : 'Active Project'})?\n\nClick OK for "This project", Cancel for "Global"`);
    const finalScope = scopeConfirm ? 'PROJECT' : 'GLOBAL';
    try {
      await Endpoints.recordCorrection({
        summary: correction.slice(0, 100),
        correction: correction,
        project_id: activeProject ? (activeProject.id || activeProject) : null,
        scope: finalScope,
      });
      const el = document.getElementById(`fb-row-${messageId}`);
      if (el) el.innerHTML = `<span style="color: #38bdf8; font-size: 0.75rem;">✓ Correction saved (${finalScope})</span>`;
    } catch (e) {
      alert('Failed to save correction: ' + e.message);
    }
  }
}

// Auto-bootstrap when document is loaded
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    const appContainer = document.getElementById('app');
    if (appContainer) {
      window.kairoApp = new KairoApp(appContainer);
      window.kairoApp.init().catch(err => {
        console.error('Kairo Command Center bootstrap failed:', err);
      });
    }
  });
}
