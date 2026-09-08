/**
 * Kairo Command Center Reactive State Store
 * Manages presentation state, active context, conversations, approvals, and security status.
 */

export class Store {
  constructor(initialState = {}) {
    this.state = {
      currentView: 'home',
      activeProject: 'Kairo',
      projects: [],
      activeSessionId: 'sess_' + Date.now().toString(36),
      conversations: [],
      isStreaming: false,
      contextPacket: null,
      activeContext: null,
      pendingApprovals: [],
      emergencyStop: {
        is_stopped: false,
        status: 'ACTIVE',
        reason: null,
      },
      emergencyStopReason: null,
      notifications: [],
      unreadNotificationCount: 0,
      unreadNotificationsCount: 0,
      capabilities: {
        web_research: true,
        browser: true,
        voice: true,
        vision: true,
        computer_control: false,
        developer_tools: true,
        automation: true,
      },
      systemHealth: {
        api: 'healthy',
        database: 'healthy',
        redis: 'healthy',
        ai_provider: 'healthy',
        version: '1.0.0',
      },
      commandPaletteOpen: false,
      contextInspectorOpen: false,
      voiceModalOpen: false,
      voiceState: 'idle', // 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
      ...initialState,
    };

    this.listeners = new Set();
  }

  getState() {
    return this.state;
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify(prevState) {
    for (const listener of this.listeners) {
      try {
        listener(this.state, prevState || this.state);
      } catch (err) {
        console.error('State subscriber error:', err);
      }
    }
  }

  setState(partial) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...partial };
    this.notify(prevState);
  }

  // --- Navigation ---
  setView(viewName) {
    this.setState({ currentView: viewName });
  }

  // --- Projects ---
  setActiveProject(project) {
    const name = typeof project === 'object' && project !== null ? (project.name || project.id) : project;
    this.setState({ activeProject: name });
  }

  setProjects(projects) {
    this.setState({ projects });
    if (!this.state.activeProject && projects && projects.length > 0) {
      const active = projects.find((p) => p.status === 'ACTIVE') || projects[0];
      this.setActiveProject(active.name || active);
    }
  }

  // --- Chat ---
  newChat() {
    this.setState({
      activeSessionId: 'sess_' + Math.random().toString(36).substring(2, 9) + Date.now().toString(36),
      conversations: [],
      isStreaming: false,
      contextPacket: null,
    });
  }

  addMessage(message) {
    const msg = {
      id: message.id || 'msg_' + Date.now().toString(36) + Math.random().toString(36).substring(2, 6),
      role: message.role || 'user',
      content: message.content || '',
      timestamp: message.timestamp || new Date().toISOString(),
      toolActivities: message.toolActivities || [],
      agentProgress: message.agentProgress || [],
      approvalRequest: message.approvalRequest || null,
      contextSummary: message.contextSummary || null,
    };

    this.setState({
      conversations: [...this.state.conversations, msg],
    });
    return msg;
  }

  addConversationMessage(message) {
    return this.addMessage(message);
  }

  getConversation() {
    return this.state.conversations;
  }

  updateLastMessageContent(chunk, append = true) {
    const msgs = [...this.state.conversations];
    if (msgs.length === 0) return;

    const last = { ...msgs[msgs.length - 1] };
    last.content = append ? last.content + chunk : chunk;
    msgs[msgs.length - 1] = last;

    this.setState({ conversations: msgs });
  }

  appendToolActivityToLastMessage(toolActivity) {
    const msgs = [...this.state.conversations];
    if (msgs.length === 0) return;

    const last = { ...msgs[msgs.length - 1] };
    last.toolActivities = [...(last.toolActivities || []), toolActivity];
    msgs[msgs.length - 1] = last;

    this.setState({ conversations: msgs });
  }

  appendAgentProgressToLastMessage(agentStep) {
    const msgs = [...this.state.conversations];
    if (msgs.length === 0) return;

    const last = { ...msgs[msgs.length - 1] };
    last.agentProgress = [...(last.agentProgress || []), agentStep];
    msgs[msgs.length - 1] = last;

    this.setState({ conversations: msgs });
  }

  setStreaming(isStreaming) {
    this.setState({ isStreaming });
  }

  // --- Context Engine ---
  setContextPacket(contextPacket) {
    this.setState({ contextPacket, activeContext: contextPacket });
  }

  setContext(contextPacket) {
    this.setContextPacket(contextPacket);
  }

  openContextInspector() {
    this.setState({ contextInspectorOpen: true });
  }

  closeContextInspector() {
    this.setState({ contextInspectorOpen: false });
  }

  // --- Security & Approvals ---
  setPendingApprovals(pendingApprovals) {
    this.setState({ pendingApprovals });
  }

  setApprovals(pendingApprovals) {
    this.setPendingApprovals(pendingApprovals);
  }

  resolveApproval(approvalId, decision) {
    const updated = this.state.pendingApprovals.filter((a) => a.id !== approvalId);
    this.setState({ pendingApprovals: updated });
  }

  removeApproval(approvalId) {
    this.resolveApproval(approvalId, 'denied');
  }

  isEmergencyStopped() {
    return !!(this.state.emergencyStop?.is_stopped);
  }

  setEmergencyStop(isStoppedOrObj, reason = null) {
    if (typeof isStoppedOrObj === 'boolean') {
      this.setState({
        emergencyStop: {
          is_stopped: isStoppedOrObj,
          status: isStoppedOrObj ? 'STOPPED' : 'ACTIVE',
          reason: reason || (isStoppedOrObj ? 'User triggered Emergency Stop' : null),
        },
        emergencyStopReason: reason || (isStoppedOrObj ? 'User triggered Emergency Stop' : null),
      });
    } else if (typeof isStoppedOrObj === 'object' && isStoppedOrObj !== null) {
      this.setState({
        emergencyStop: isStoppedOrObj,
        emergencyStopReason: isStoppedOrObj.reason || null,
      });
    }
  }

  setCapability(capKey, value) {
    this.setState({
      capabilities: {
        ...this.state.capabilities,
        [capKey]: !!value,
      },
    });
  }

  toggleCapability(capKey) {
    const current = !!this.state.capabilities[capKey];
    this.setCapability(capKey, !current);
  }

  // --- Notifications ---
  setNotifications(notifications) {
    const unreadCount = (notifications || []).filter((n) => !n.is_read && n.status !== 'read' && n.status !== 'dismissed').length;
    this.setState({
      notifications,
      unreadNotificationCount: unreadCount,
      unreadNotificationsCount: unreadCount,
    });
  }

  addNotification(notification) {
    const list = [notification, ...this.state.notifications];
    const unreadCount = list.filter((n) => !n.is_read && n.status !== 'read' && n.status !== 'dismissed').length;
    this.setState({
      notifications: list,
      unreadNotificationCount: unreadCount,
      unreadNotificationsCount: unreadCount,
    });
  }

  setUnreadNotificationsCount(count) {
    this.setState({
      unreadNotificationCount: count,
      unreadNotificationsCount: count,
    });
  }

  markNotificationAsRead(id) {
    const updated = this.state.notifications.map((n) => (n.id === id ? { ...n, is_read: true, status: 'read' } : n));
    const unreadCount = updated.filter((n) => !n.is_read && n.status !== 'read' && n.status !== 'dismissed').length;
    this.setState({
      notifications: updated,
      unreadNotificationCount: unreadCount,
      unreadNotificationsCount: unreadCount,
    });
  }

  // --- System Health ---
  setSystemHealth(systemHealth) {
    this.setState({ systemHealth });
  }

  // --- Modals & Dialogs ---
  openCommandPalette() {
    this.setState({ commandPaletteOpen: true });
  }

  closeCommandPalette() {
    this.setState({ commandPaletteOpen: false });
  }

  openVoiceModal() {
    this.setState({ voiceModalOpen: true, voiceState: 'listening' });
  }

  closeVoiceModal() {
    this.setState({ voiceModalOpen: false, voiceState: 'idle' });
  }

  setVoiceState(voiceState) {
    this.setState({ voiceState });
  }
}

export const store = new Store();
