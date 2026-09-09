/**
 * Kairo Endpoint Definitions
 * Maps frontend interactions directly to existing authoritative backend routes.
 */

import { api } from './client.js';

export const Endpoints = {
  // --- Chat ---
  async sendMessage({ message, session_id = null, capability = null, model = null }) {
    return api.post('/api/v1/chat', {
      message,
      session_id,
      capability,
      model,
    });
  },

  async streamMessage({ message, session_id = null, onChunk, onComplete, onError }) {
    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': api.userId,
        },
        body: JSON.stringify({ message, session_id }),
      });

      if (!response.ok) {
        throw new Error(`Streaming failed: HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6).trim();
            if (raw === '[DONE]') {
              if (onComplete) onComplete();
              return;
            }
            try {
              const parsed = JSON.parse(raw);
              if (onChunk) onChunk(parsed);
            } catch (err) {
              if (onChunk) onChunk({ token: raw });
            }
          }
        }
      }
      if (onComplete) onComplete();
    } catch (err) {
      if (onError) onError(err);
      else throw err;
    }
  },

  // --- Context Engine ---
  async getCurrentContext(sessionId = null) {
    const q = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
    return api.get(`/api/v1/context/current${q}`);
  },

  async getProjectContext(projectId) {
    return api.get(`/api/v1/context/projects/${encodeURIComponent(projectId)}`);
  },

  async searchContext(query) {
    return api.get(`/api/v1/context/search?q=${encodeURIComponent(query)}`);
  },

  async getContextSettings() {
    return api.get('/api/v1/context/settings');
  },

  async updateContextSettings(settingsUpdate) {
    return api.patch('/api/v1/context/settings', settingsUpdate);
  },

  // --- Projects ---
  async listProjects(statusFilter = null) {
    const q = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : '';
    return api.get(`/api/v1/projects${q}`);
  },

  async getProject(projectId) {
    return api.get(`/api/v1/projects/${encodeURIComponent(projectId)}`);
  },

  async createProject(projectData) {
    return api.post('/api/v1/projects', projectData);
  },

  async updateProject(projectId, updateData) {
    return api.patch(`/api/v1/projects/${encodeURIComponent(projectId)}`, updateData);
  },

  async deleteProject(projectId) {
    return api.delete(`/api/v1/projects/${encodeURIComponent(projectId)}`);
  },

  async linkProjectRepository(projectId, { repository_path, is_primary = false }) {
    return api.post(`/api/v1/projects/${encodeURIComponent(projectId)}/repositories`, {
      repository_path,
      is_primary,
    });
  },

  async linkProjectWorkflow(projectId, workflowId) {
    return api.post(`/api/v1/projects/${encodeURIComponent(projectId)}/workflows`, {
      workflow_id: workflowId,
    });
  },

  // --- Security Center ---
  async getSecurityCapabilities() {
    return api.get('/api/v1/security/capabilities');
  },

  async getEmergencyStopStatus() {
    return api.get('/api/v1/security/emergency-stop');
  },

  async triggerEmergencyStop(reason = 'User initiated emergency stop via Command Center') {
    return api.post('/api/v1/security/emergency-stop', { reason });
  },

  async resetEmergencyStop() {
    return api.delete('/api/v1/security/emergency-stop');
  },

  async listPendingApprovals() {
    return api.get('/api/v1/security/approvals/pending');
  },

  async decideApproval(approvalId, decision, reason = null) {
    return api.post(`/api/v1/security/approvals/${encodeURIComponent(approvalId)}/decide`, {
      decision,
      reason,
    });
  },

  async listAuditEvents(limit = 25) {
    return api.get(`/api/v1/security/audit/events?limit=${limit}`);
  },

  // --- Memory ---
  async listMemories(memoryType = null, limit = 50) {
    let q = `?limit=${limit}`;
    if (memoryType) q += `&memory_type=${encodeURIComponent(memoryType)}`;
    return api.get(`/api/v1/memory${q}`);
  },

  async getMemory(memoryId) {
    return api.get(`/api/v1/memory/${encodeURIComponent(memoryId)}`);
  },

  async updateMemory(memoryId, updateData) {
    return api.patch(`/api/v1/memory/${encodeURIComponent(memoryId)}`, updateData);
  },

  async deleteMemory(memoryId) {
    return api.delete(`/api/v1/memory/${encodeURIComponent(memoryId)}`);
  },

  // --- Automations ---
  async listWorkflows() {
    return api.get('/api/v1/automations');
  },

  async createWorkflow(workflowData) {
    return api.post('/api/v1/automations', workflowData);
  },

  async getWorkflow(workflowId) {
    return api.get(`/api/v1/automations/${encodeURIComponent(workflowId)}`);
  },

  async updateWorkflow(workflowId, updateData) {
    return api.patch(`/api/v1/automations/${encodeURIComponent(workflowId)}`, updateData);
  },

  async deleteWorkflow(workflowId) {
    return api.delete(`/api/v1/automations/${encodeURIComponent(workflowId)}`);
  },

  async triggerWorkflow(workflowId) {
    return api.post(`/api/v1/automations/${encodeURIComponent(workflowId)}/run`);
  },

  async getWorkflowRuns(workflowId, limit = 10) {
    return api.get(`/api/v1/automations/${encodeURIComponent(workflowId)}/runs?limit=${limit}`);
  },

  // --- Notifications & Proactive Insights ---
  async listNotifications(unreadOnly = false) {
    const q = unreadOnly ? '?status=unread' : '';
    return api.get(`/api/v1/notifications${q}`);
  },

  async markNotificationRead(notificationId) {
    return api.post(`/api/v1/notifications/${encodeURIComponent(notificationId)}/read`);
  },

  async dismissNotification(notificationId) {
    return api.post(`/api/v1/notifications/${encodeURIComponent(notificationId)}/dismiss`);
  },

  // --- Observability & System Status ---
  async getSystemLive() {
    return api.get('/health/live');
  },

  async getSystemReady() {
    return api.get('/health/ready');
  },

  async getSystemVersion() {
    return api.get('/health/version');
  },

  // --- Devices & Local Companion ---
  async listDevices(includeRevoked = false) {
    return api.get(`/api/v1/devices?include_revoked=${includeRevoked}`);
  },

  async getDevice(deviceId) {
    return api.get(`/api/v1/devices/${encodeURIComponent(deviceId)}`);
  },

  async registerDevice(deviceData) {
    return api.post('/api/v1/devices/register', deviceData);
  },

  async updateDevice(deviceId, updateData) {
    return api.patch(`/api/v1/devices/${encodeURIComponent(deviceId)}`, updateData);
  },

  async revokeDevice(deviceId) {
    return api.post(`/api/v1/devices/${encodeURIComponent(deviceId)}/revoke`);
  },

  async dispatchDeviceCommand(deviceId, commandData) {
    return api.post(`/api/v1/devices/${encodeURIComponent(deviceId)}/commands`, commandData);
  },

  // --- Knowledge Fabric (Task 25) ---
  async searchKnowledge({ query, projectId = null, type = null, sourceType = null, limit = 15 }) {
    let q = `?q=${encodeURIComponent(query)}&limit=${limit}`;
    if (projectId) q += `&project_id=${encodeURIComponent(projectId)}`;
    if (type) q += `&type=${encodeURIComponent(type)}`;
    if (sourceType) q += `&source_type=${encodeURIComponent(sourceType)}`;
    return api.get(`/api/v1/knowledge/search${q}`);
  },

  async getKnowledgeNode(nodeId) {
    return api.get(`/api/v1/knowledge/${encodeURIComponent(nodeId)}`);
  },

  async getKnowledgeRelationships(nodeId) {
    return api.get(`/api/v1/knowledge/${encodeURIComponent(nodeId)}/relationships`);
  },

  async getKnowledgeSources(nodeId) {
    return api.get(`/api/v1/knowledge/${encodeURIComponent(nodeId)}/sources`);
  },

  async getKnowledgeTimeline({ projectId = null, type = null, limit = 50 } = {}) {
    let q = `?limit=${limit}`;
    if (projectId) q += `&project_id=${encodeURIComponent(projectId)}`;
    if (type) q += `&type=${encodeURIComponent(type)}`;
    return api.get(`/api/v1/knowledge/timeline${q}`);
  },

  async getKnowledgeGraph(nodeId, depth = 2) {
    return api.get(`/api/v1/knowledge/${encodeURIComponent(nodeId)}/graph?depth=${depth}`);
  },

  async listDecisions(projectId = null) {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
    return api.get(`/api/v1/knowledge/decisions${q}`);
  },

  async createDecision(decisionData) {
    return api.post('/api/v1/knowledge/decisions', decisionData);
  },

  async supersedeDecision(decisionId, supersedeData) {
    return api.post(`/api/v1/knowledge/decisions/${encodeURIComponent(decisionId)}/supersede`, supersedeData);
  },

  async uploadKnowledgeDocument(formData) {
    // Note: formData handled via multipart fetch with x-user-id
    const res = await fetch('/api/v1/knowledge/documents/upload', {
      method: 'POST',
      headers: {
        'x-user-id': api.userId,
      },
      body: formData,
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Upload failed with status ${res.status}`);
    }
    return res.json();
  },

  async getDocumentIndexingStatus(jobId) {
    return api.get(`/api/v1/knowledge/documents/${encodeURIComponent(jobId)}/status`);
  },

  async triggerKnowledgeBackfill() {
    return api.post('/api/v1/knowledge/backfill');
  },

  async deleteKnowledgeNode(nodeId) {
    return api.delete(`/api/v1/knowledge/${encodeURIComponent(nodeId)}`);
  },

  async getKnowledgeConflicts(projectId = null) {
    const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
    return api.get(`/api/v1/knowledge/conflicts${q}`);
  },
};

