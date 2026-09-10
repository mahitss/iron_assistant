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
  async listNotifications(unreadOnly = false, typeFilter = null, priorityFilter = null) {
    const params = new URLSearchParams();
    if (unreadOnly) params.set('status', 'unread');
    if (typeFilter) params.set('type', typeFilter);
    if (priorityFilter) params.set('priority', priorityFilter);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return api.get(`/api/v1/notifications${qs}`);
  },

  async getNotification(notificationId) {
    return api.get(`/api/v1/notifications/${encodeURIComponent(notificationId)}`);
  },

  async markNotificationRead(notificationId) {
    return api.post(`/api/v1/notifications/${encodeURIComponent(notificationId)}/read`);
  },

  async dismissNotification(notificationId) {
    return api.post(`/api/v1/notifications/${encodeURIComponent(notificationId)}/dismiss`);
  },

  async markAllNotificationsRead() {
    return api.post('/api/v1/notifications/read-all');
  },

  async executeNotificationAction(notificationId, actionId, reason = null) {
    return api.post(`/api/v1/notifications/${encodeURIComponent(notificationId)}/action`, {
      action_id: actionId,
      reason,
    });
  },

  async getNotificationPreferences() {
    return api.get('/api/v1/notifications/preferences');
  },

  async updateNotificationPreferences(preferences) {
    return api.put('/api/v1/notifications/preferences', preferences);
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

  // --- Skills & Capabilities (Task 26) ---
  async listSkills(category = null, enabledOnly = false) {
    let q = `?enabled_only=${enabledOnly}`;
    if (category) q += `&category=${encodeURIComponent(category)}`;
    return api.get(`/api/v1/skills${q}`);
  },

  async getSkillDetail(skillId) {
    return api.get(`/api/v1/skills/${encodeURIComponent(skillId)}`);
  },

  async getSkillHealth(skillId) {
    return api.get(`/api/v1/skills/${encodeURIComponent(skillId)}/health`);
  },

  async executeSkill(skillId, payload = {}) {
    return api.post(`/api/v1/skills/${encodeURIComponent(skillId)}/execute`, payload);
  },

  async getSkillExecutionStatus(executionId) {
    return api.get(`/api/v1/skills/executions/${encodeURIComponent(executionId)}`);
  },

  async cancelSkillExecution(executionId) {
    return api.post(`/api/v1/skills/executions/${encodeURIComponent(executionId)}/cancel`);
  },

  async toggleSkill(skillId, enabled) {
    return api.post(`/api/v1/skills/${encodeURIComponent(skillId)}/toggle`, { enabled });
  },

  // --- Evaluation & Benchmarking (Task 27) ---
  async listEvaluationScenarios(category = null, suite = null) {
    let q = '';
    if (category) q += `?category=${encodeURIComponent(category)}`;
    else if (suite) q += `?suite=${encodeURIComponent(suite)}`;
    return api.get(`/api/v1/evaluation/scenarios${q}`);
  },

  async listEvaluationSuites() {
    return api.get('/api/v1/evaluation/suites');
  },

  async runEvaluation(suite = 'full', scenarioId = null, multiRunCount = 1) {
    return api.post('/api/v1/evaluation/run', {
      suite,
      scenario_id: scenarioId,
      multi_run_count: multiRunCount,
    });
  },

  async listEvaluationRuns() {
    return api.get('/api/v1/evaluation/runs');
  },

  async getEvaluationRunDetail(runId) {
    return api.get(`/api/v1/evaluation/runs/${encodeURIComponent(runId)}`);
  },

  async getEvaluationBaselines() {
    return api.get('/api/v1/evaluation/baselines');
  },

  async compareEvaluationRun(runId = null, baselineVersion = 'v1.0.0') {
    let q = `?baseline_version=${encodeURIComponent(baselineVersion)}`;
    if (runId) q += `&run_id=${encodeURIComponent(runId)}`;
    return api.get(`/api/v1/evaluation/compare${q}`);
  },

  async getSecurityEvaluationDashboard() {
    return api.get('/api/v1/evaluation/security');
  },

  // --- Unified Event Bus (Task 28) ---
  async getEventRegistryCatalog() {
    return api.get('/api/v1/events/registry');
  },

  async getEventBusMetrics() {
    return api.get('/api/v1/events/metrics');
  },

  async listDeadLetters(status = null, limit = 50, offset = 0) {
    let q = `?limit=${limit}&offset=${offset}`;
    if (status) q += `&status=${encodeURIComponent(status)}`;
    return api.get(`/api/v1/events/dead-letters${q}`);
  },

  async getDeadLetterDetail(deadLetterId) {
    return api.get(`/api/v1/events/dead-letters/${encodeURIComponent(deadLetterId)}`);
  },

  async replayDeadLetter(deadLetterId, force = false, reason = null) {
    return api.post(`/api/v1/events/dead-letters/${encodeURIComponent(deadLetterId)}/replay`, {
      force,
      reason,
    });
  },

  async discardDeadLetter(deadLetterId, reason = null) {
    let q = reason ? `?reason=${encodeURIComponent(reason)}` : '';
    return api.post(`/api/v1/events/dead-letters/${encodeURIComponent(deadLetterId)}/discard${q}`);
  },

  async getActivityTimeline(limit = 50, offset = 0) {
    return api.get(`/api/v1/events/activity?limit=${limit}&offset=${offset}`);
  },

  async publishEvent(eventType, source = 'web_client', payload = {}, correlationId = null, metadata = null) {
    return api.post('/api/v1/events/publish', {
      event_type: eventType,
      source,
      payload,
      correlation_id: correlationId,
      metadata,
    });
  },

  // --- Feedback & Experience Learning (Task 29) ---
  async submitFeedback({ feedback_type, session_id = null, message_id = null, rating = null, comment = null, correction = null }) {
    return api.post('/api/v1/feedback', {
      feedback_type,
      session_id,
      message_id,
      rating,
      comment,
      correction,
    });
  },

  async listFeedback(feedbackType = null, limit = 50, offset = 0) {
    let q = `?limit=${limit}&offset=${offset}`;
    if (feedbackType) q += `&feedback_type=${encodeURIComponent(feedbackType)}`;
    return api.get(`/api/v1/feedback${q}`);
  },

  async getFeedback(feedbackId) {
    return api.get(`/api/v1/feedback/${encodeURIComponent(feedbackId)}`);
  },

  async listExperiences({ projectId = null, type = null, status = null, scope = null, limit = 50, offset = 0 } = {}) {
    let params = new URLSearchParams();
    if (projectId) params.set('project_id', projectId);
    if (type) params.set('experience_type', type);
    if (status) params.set('status_filter', status);
    if (scope) params.set('scope', scope);
    params.set('limit', limit);
    params.set('offset', offset);
    return api.get(`/api/v1/experience?${params.toString()}`);
  },

  async getExperience(experienceId) {
    return api.get(`/api/v1/experience/${encodeURIComponent(experienceId)}`);
  },

  async recordCorrection({ summary, correction, project_id = null, scope = 'PROJECT', temporal_hours = null }) {
    return api.post('/api/v1/experience/corrections', {
      summary,
      correction,
      project_id,
      scope,
      temporal_hours,
    });
  },

  async supersedeExperience(experienceId, supersededById) {
    return api.post(`/api/v1/experience/${encodeURIComponent(experienceId)}/supersede?superseded_by_id=${encodeURIComponent(supersededById)}`);
  },

  async deleteExperience(experienceId) {
    return api.delete(`/api/v1/experience/${encodeURIComponent(experienceId)}`);
  },

  async setPreference({ key, value, scope = 'USER', source = 'USER_EXPLICIT' }) {
    return api.post('/api/v1/experience/preferences', {
      key,
      value,
      scope,
      source,
    });
  },

  async listPreferences(scope = null) {
    const q = scope ? `?scope=${encodeURIComponent(scope)}` : '';
    return api.get(`/api/v1/experience/preferences${q}`);
  },

  async deletePreference(key, scope = 'USER') {
    return api.delete(`/api/v1/experience/preferences/${encodeURIComponent(key)}?scope=${encodeURIComponent(scope)}`);
  },

  async exportExperienceData() {
    return api.get('/api/v1/experience/export');
  },

  async listLearningCandidates(statusFilter = null, limit = 50) {
    let q = `?limit=${limit}`;
    if (statusFilter) q += `&status_filter=${encodeURIComponent(statusFilter)}`;
    return api.get(`/api/v1/experience/candidates${q}`);
  },

  async reviewLearningCandidate(candidateId, decision, reviewNotes = null) {
    return api.post(`/api/v1/experience/candidates/${encodeURIComponent(candidateId)}/review`, {
      decision,
      review_notes: reviewNotes,
    });
  },

  async getFailureAnalytics(days = 30, skill = null, tool = null, projectId = null) {
    let params = new URLSearchParams({ days: days.toString() });
    if (skill) params.set('skill', skill);
    if (tool) params.set('tool', tool);
    if (projectId) params.set('project_id', projectId);
    return api.get(`/api/v1/experience/analytics/failures?${params.toString()}`);
  },

  async getSuccessAnalytics(days = 30, skill = null, tool = null, projectId = null) {
    let params = new URLSearchParams({ days: days.toString() });
    if (skill) params.set('skill', skill);
    if (tool) params.set('tool', tool);
    if (projectId) params.set('project_id', projectId);
    return api.get(`/api/v1/experience/analytics/successes?${params.toString()}`);
  },


  async analyzeMultimodal({ prompt, project_id = null, device_id = null, capture_screen = false, attachments = [] }) {
    return api.post('/api/v1/multimodal/analyze', {
      prompt,
      project_id,
      device_id,
      capture_screen,
      attachments,
    });
  },

  async transcribeAudio({ device_id = null, audio_format = 'wav', audio_base64 = null, duration_seconds = null }) {
    return api.post('/api/v1/multimodal/transcribe', {
      device_id,
      audio_format,
      audio_base64,
      duration_seconds,
    });
  },

  async processMultimodal({ query = null, project_id = null, device_id = null, media_type = 'image', media_base64 = null, filename = null }) {
    return api.post('/api/v1/multimodal/process', {
      query,
      project_id,
      device_id,
      media_type,
      media_base64,
      filename,
    });
  },

  async getMultimodalRequest(requestId) {
    return api.get(`/api/v1/multimodal/${encodeURIComponent(requestId)}`);
  },

  // --- Autonomous Task Engine (Task 31) ---
  async createTask({ objective, project_id = null, priority = 'NORMAL', autonomy_level = 'SUPERVISED', budget = null, deadline = null, dry_run = false, metadata = {} }) {
    return api.post('/api/v1/tasks', {
      objective,
      project_id,
      priority,
      autonomy_level,
      budget,
      deadline,
      dry_run,
      metadata,
    });
  },

  async getTasks({ status = null, project_id = null, limit = 50, offset = 0 } = {}) {
    let params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
    if (status) params.set('status', status);
    if (project_id) params.set('project_id', project_id);
    return api.get(`/api/v1/tasks?${params.toString()}`);
  },

  async getTask(taskId) {
    return api.get(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
  },

  async pauseTask(taskId) {
    return api.post(`/api/v1/tasks/${encodeURIComponent(taskId)}/pause`, {});
  },

  async resumeTask(taskId) {
    return api.post(`/api/v1/tasks/${encodeURIComponent(taskId)}/resume`, {});
  },

  async cancelTask(taskId) {
    return api.post(`/api/v1/tasks/${encodeURIComponent(taskId)}/cancel`, {});
  },

  async retryTask(taskId) {
    return api.post(`/api/v1/tasks/${encodeURIComponent(taskId)}/retry`, {});
  },

  async approveTaskStep(taskId, { approved, reason = '' }) {
    return api.post(`/api/v1/tasks/${encodeURIComponent(taskId)}/approve`, { approved, reason });
  },

  async respondToTask(taskId, responseText) {
    return api.post(`/api/v1/tasks/${encodeURIComponent(taskId)}/respond`, { response: responseText });
  },

  async getTaskActivity(taskId) {
    return api.get(`/api/v1/tasks/${encodeURIComponent(taskId)}/activity`);
  },

  async getTaskPlans(taskId) {
    return api.get(`/api/v1/tasks/${encodeURIComponent(taskId)}/plan`);
  },

  // --- World Model & Environment State (Task 32) ---
  async getWorldOverview() {
    return api.get('/api/v1/world');
  },

  async getWorldProject(projectId) {
    return api.get(`/api/v1/world/projects/${encodeURIComponent(projectId)}`);
  },

  async getWorldEntity(entityId) {
    return api.get(`/api/v1/world/entities/${encodeURIComponent(entityId)}`);
  },

  async getWorldDependencies(entityId, maxDepth = 3) {
    return api.get(`/api/v1/world/entities/${encodeURIComponent(entityId)}/dependencies?max_depth=${maxDepth}`);
  },

  async getWorldChanges({ sinceSeconds = 3600, projectId = null } = {}) {
    let params = new URLSearchParams({ since_seconds: sinceSeconds.toString() });
    if (projectId) params.set('project_id', projectId);
    return api.get(`/api/v1/world/changes?${params.toString()}`);
  },

  async refreshWorld(entityId = null) {
    let params = entityId ? `?entity_id=${encodeURIComponent(entityId)}` : '';
    return api.post(`/api/v1/world/refresh${params}`, {});
  },

  async createWorldSnapshot(projectId = null) {
    return api.post('/api/v1/world/snapshots', { project_id: projectId });
  },

  async getWorldHealth() {
    return api.get('/api/v1/world/health');
  },

  // --- Identity, Sessions, Device Trust, Presence & Handoff (Task 33) ---
  async getSessions(includeRevoked = false) {
    return api.get(`/api/v1/identity/sessions?include_revoked=${includeRevoked}`);
  },

  async createSession({ client_type, device_id = null, metadata = {} }) {
    return api.post('/api/v1/identity/sessions', { client_type, device_id, metadata });
  },

  async revokeSession(sessionId, reason = 'User initiated revocation') {
    return api.post(`/api/v1/identity/sessions/${encodeURIComponent(sessionId)}/revoke`, { reason });
  },

  async revokeAllSessions(exceptSessionId = null) {
    let params = exceptSessionId ? `?except_session_id=${encodeURIComponent(exceptSessionId)}` : '';
    return api.post(`/api/v1/identity/sessions/revoke-all${params}`, {});
  },

  async getPresence() {
    return api.get('/api/v1/identity/presence');
  },

  async sendPresenceHeartbeat({ session_id, device_id = null, interface_name = 'WEB', state = 'ACTIVE' }) {
    return api.post('/api/v1/identity/presence/heartbeat', {
      session_id,
      device_id,
      interface: interface_name,
      state,
    });
  },

  async getOnlineStatus() {
    return api.get('/api/v1/identity/presence/online-status');
  },

  async createHandoff({ source_session_id, target_device_id = null, conversation_id = null, task_id = null, project_id = null, explicit_consent = true }) {
    return api.post('/api/v1/identity/handoff', {
      source_session_id,
      target_device_id,
      conversation_id,
      task_id,
      project_id,
      explicit_consent,
    });
  },

  async completeHandoff(handoffId, handoffToken, targetSessionId) {
    return api.post(`/api/v1/identity/handoff/${encodeURIComponent(handoffId)}/complete`, {
      handoff_token: handoffToken,
      target_session_id: targetSessionId,
    });
  },

  async resolveTaskContinuity(taskId = null, projectId = null) {
    let params = new URLSearchParams();
    if (taskId) params.set('task_id', taskId);
    if (projectId) params.set('project_id', projectId);
    return api.get(`/api/v1/identity/continuity/task?${params.toString()}`);
  },

  async resolveDeviceTarget(deviceId = null, capability = null) {
    let params = new URLSearchParams();
    if (deviceId) params.set('device_id', deviceId);
    if (capability) params.set('capability', capability);
    return api.get(`/api/v1/identity/continuity/device?${params.toString()}`);
  },

  async trustDevice(deviceId, trustStatus = 'TRUSTED', expiresInDays = 90) {
    return api.post(`/api/v1/devices/${encodeURIComponent(deviceId)}/trust`, {
      trust_status: trustStatus,
      expires_in_days: expiresInDays,
    });
  },

  async initiateDevicePairing(deviceName = null, clientType = 'LOCAL_COMPANION', capabilities = []) {
    return api.post('/api/v1/devices/pair', {
      device_name: deviceName,
      client_type: clientType,
      capabilities,
    });
  },

  async consumeDevicePairing(deviceId, pairingCode, publicKey = null) {
    return api.post('/api/v1/devices/pair/consume', {
      device_id: deviceId,
      pairing_code: pairingCode,
      public_key: publicKey,
    });
  },

  // Unified Command & Intent Layer (Task 35, Spec 122)
  async sendCommand({ text, session_id = null, conversation_id = null, attachments = [], source_interface = 'WEB', project_hint = null, clarification_response = null }) {
    return api.post('/api/v1/commands', {
      text,
      session_id,
      conversation_id,
      attachments,
      source_interface,
      project_hint,
      clarification_response,
    });
  },

  async resolveCommand({ text, session_id = null, conversation_id = null, attachments = [], source_interface = 'WEB', project_hint = null }) {
    return api.post('/api/v1/commands/resolve', {
      text,
      session_id,
      conversation_id,
      attachments,
      source_interface,
      project_hint,
    });
  },

  async getCommand(commandId) {
    return api.get(`/api/v1/commands/${encodeURIComponent(commandId)}`);
  },

  // Policy, Governance, Risk, and Authorization Engine (Task 36)
  async evaluatePolicy(context, simulate = false) {
    return api.post('/api/v1/policy/evaluate', {
      context,
      simulate,
    });
  },

  async simulatePolicy(context, candidatePolicy = null) {
    return api.post('/api/v1/policy/simulate', {
      context,
      candidate_policy: candidatePolicy,
    });
  },

  async getPolicyDecision(evaluationId) {
    return api.get(`/api/v1/policy/decision/${encodeURIComponent(evaluationId)}`);
  },

  async getPolicyStatus() {
    return api.get('/api/v1/policy/status');
  },

  async listPolicies(includeDisabled = true) {
    return api.get(`/api/v1/admin/policies?include_disabled=${includeDisabled}`);
  },

  async createPolicy(policyData) {
    return api.post('/api/v1/admin/policies', policyData);
  },

  async updatePolicy(policyId, updateData) {
    return api.put(`/api/v1/admin/policies/${encodeURIComponent(policyId)}`, updateData);
  },

  async activatePolicy(policyId) {
    return api.post(`/api/v1/admin/policies/${encodeURIComponent(policyId)}/activate`);
  },

  async disablePolicy(policyId) {
    return api.post(`/api/v1/admin/policies/${encodeURIComponent(policyId)}/disable`);
  },

  async rollbackPolicy(policyId, targetVersion, reason) {
    return api.post(`/api/v1/admin/policies/${encodeURIComponent(policyId)}/rollback`, {
      target_version: targetVersion,
      reason,
    });
  },

  async setChangeFreeze(environment, active, reason = '') {
    const params = new URLSearchParams({
      environment,
      active: active ? 'true' : 'false',
      reason,
    });
    return api.post(`/api/v1/admin/freeze?${params.toString()}`);
  },

  async toggleSafeMode(enabled) {
    const params = new URLSearchParams({
      enabled: enabled ? 'true' : 'false',
    });
    return api.post(`/api/v1/admin/safemode?${params.toString()}`);
  },

  // ============================================================================
  // Resilience & Fault-Tolerance Endpoints (Task 37)
  // ============================================================================

  async getResilienceHealth() {
    return api.get('/api/v1/resilience/health');
  },

  async getResilienceDashboard() {
    return api.get('/api/v1/resilience/dashboard');
  },

  async listCircuitBreakers() {
    return api.get('/api/v1/resilience/circuits');
  },

  async resetCircuitBreaker(circuitId) {
    return api.post(`/api/v1/resilience/circuits/${encodeURIComponent(circuitId)}/reset`);
  },

  async listQuarantinedTasks() {
    return api.get('/api/v1/resilience/quarantine');
  },

  async releaseQuarantinedTask(taskId, releasedBy = 'operator') {
    return api.post(`/api/v1/resilience/quarantine/${encodeURIComponent(taskId)}/release?released_by=${encodeURIComponent(releasedBy)}`);
  },

  async recoverTask(taskId, workerId = 'worker-ui', policyVersion = 1) {
    return api.post(`/api/v1/resilience/tasks/${encodeURIComponent(taskId)}/recover?worker_id=${encodeURIComponent(workerId)}&current_policy_version=${policyVersion}`);
  },

  async setReadOnlyDegradation(enabled) {
    return api.post(`/api/v1/resilience/degradation/read-only?enabled=${enabled ? 'true' : 'false'}`);
  },

  // Observability & System Intelligence (Task 38)
  async getObservabilityHealth() {
    return api.get('/api/v1/observability/health-score');
  },

  async getObservabilityDashboard() {
    return api.get('/api/v1/observability/dashboard');
  },

  async getTrace(traceId) {
    return api.get(`/api/v1/observability/traces/${encodeURIComponent(traceId)}`);
  },

  async getTaskTrace(taskId) {
    return api.get(`/api/v1/observability/tasks/${encodeURIComponent(taskId)}`);
  },

  async listIncidents(statusFilter = null) {
    const q = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
    return api.get(`/api/v1/observability/incidents${q}`);
  },

  async getIncident(incidentId) {
    return api.get(`/api/v1/observability/incidents/${encodeURIComponent(incidentId)}`);
  },

  async acknowledgeIncident(incidentId, acknowledgedBy = 'operator') {
    return api.post(`/api/v1/observability/incidents/${encodeURIComponent(incidentId)}/acknowledge`, {
      acknowledged_by: acknowledgedBy,
    });
  },

  async resolveIncident(incidentId, recoveryEvidence) {
    return api.post(`/api/v1/observability/incidents/${encodeURIComponent(incidentId)}/resolve`, {
      recovery_evidence: recoveryEvidence,
    });
  },

  async getDependencies() {
    return api.get('/api/v1/observability/dependencies');
  },

  async runDiagnostics(targetRef) {
    return api.post('/api/v1/observability/diagnose', { target_ref: targetRef });
  },

  async runRootCauseAnalysis(targetRef) {
    return api.post('/api/v1/observability/root-cause', { target_ref: targetRef });
  },

  // --- State Fabric (Task 39) ---
  async getStateHealth() {
    return api.get('/api/v1/state/health');
  },

  async getStateRecord(domain, resourceType, resourceId, consistency = 'STRONG') {
    return api.get(
      `/api/v1/state/records/${encodeURIComponent(domain)}/${encodeURIComponent(resourceType)}/${encodeURIComponent(resourceId)}?consistency=${encodeURIComponent(consistency)}`
    );
  },

  async getStateChangelog(resourceType = null, resourceId = null, limit = 50) {
    const params = new URLSearchParams();
    if (resourceType) params.append('resource_type', resourceType);
    if (resourceId) params.append('resource_id', resourceId);
    params.append('limit', limit.toString());
    return api.get(`/api/v1/state/changelog?${params.toString()}`);
  },

  async triggerStateReconciliation(mode = 'CHECK') {
    return api.post(`/api/v1/state/reconcile?mode=${encodeURIComponent(mode)}`);
  },

  async getLastStateReconciliation() {
    return api.get('/api/v1/state/reconcile/last');
  },

  async listStateQuarantine() {
    return api.get('/api/v1/state/quarantine');
  },

  async releaseStateQuarantine(resourceId, operator = 'operator') {
    return api.post(
      `/api/v1/state/quarantine/${encodeURIComponent(resourceId)}/release?operator=${encodeURIComponent(operator)}`
    );
  },

  // --- Cognitive Planning & Reasoning Engine (Task 41) ---
  async createCognitiveGoal(payload) {
    return api.post('/api/v1/cognition/goals', payload);
  },

  async getCognitiveGoal(goalId) {
    return api.get(`/api/v1/cognition/goals/${encodeURIComponent(goalId)}`);
  },

  async buildCognitivePlan(goalId, payload = {}) {
    return api.post(`/api/v1/cognition/goals/${encodeURIComponent(goalId)}/plan`, payload);
  },

  async getCognitivePlan(planId) {
    return api.get(`/api/v1/cognition/plans/${encodeURIComponent(planId)}`);
  },

  async validateCognitivePlan(planId) {
    return api.post(`/api/v1/cognition/plans/${encodeURIComponent(planId)}/validate`);
  },

  async replanCognitivePlan(planId, payload) {
    return api.post(`/api/v1/cognition/plans/${encodeURIComponent(planId)}/replan`, payload);
  },

  async verifyCognitiveStep(planId, payload) {
    return api.post(`/api/v1/cognition/plans/${encodeURIComponent(planId)}/verify-step`, payload);
  },

  async getCognitivePlanPreview(planId) {
    return api.get(`/api/v1/cognition/plans/${encodeURIComponent(planId)}/preview`);
  },

  async explainCognitiveStep(planId, stepId) {
    return api.get(`/api/v1/cognition/plans/${encodeURIComponent(planId)}/steps/${encodeURIComponent(stepId)}/explain`);
  },

  async getCognitiveDashboard() {
    return api.get('/api/v1/cognition/dashboard');
  },

  async listCognitiveTemplates() {
    return api.get('/api/v1/cognition/templates');
  },

  // --- Truth, Verification & Self-Correction Engine (Task 42) ---
  async createVerificationClaim(payload) {
    return api.post('/api/v1/verification/claims', payload);
  },

  async listVerificationClaims(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/verification/claims${qs ? `?${qs}` : ''}`);
  },

  async getVerificationClaim(claimId) {
    return api.get(`/api/v1/verification/claims/${encodeURIComponent(claimId)}`);
  },

  async registerVerificationEvidence(payload) {
    return api.post('/api/v1/verification/evidence', payload);
  },

  async getVerificationEvidence(evidenceId) {
    return api.get(`/api/v1/verification/evidence/${encodeURIComponent(evidenceId)}`);
  },

  async verifyClaimContract(claimId, payload) {
    return api.post(`/api/v1/verification/claims/${encodeURIComponent(claimId)}/verify`, payload);
  },

  async triangulateClaim(claimId) {
    return api.get(`/api/v1/verification/claims/${encodeURIComponent(claimId)}/triangulate`);
  },

  async getClaimConfidence(claimId) {
    return api.get(`/api/v1/verification/claims/${encodeURIComponent(claimId)}/confidence`);
  },

  async getClaimContradictions(claimId) {
    return api.get(`/api/v1/verification/claims/${encodeURIComponent(claimId)}/contradictions`);
  },

  async submitSelfCorrection(payload) {
    return api.post('/api/v1/verification/corrections', payload);
  },

  async validateCitation(payload) {
    return api.post('/api/v1/verification/citations/validate', payload);
  },

  async evaluateInvariants(payload) {
    return api.post('/api/v1/verification/invariants/evaluate', payload);
  },

  async getVerificationStats() {
    return api.get('/api/v1/verification/stats');
  },

  // --- Adaptive Learning & Strategy Optimization Engine (Task 43) ---
  async listLearningStrategies(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/strategies${qs ? `?${qs}` : ''}`);
  },

  async getLearningStrategy(strategyId) {
    return api.get(`/api/v1/learning/strategies/${encodeURIComponent(strategyId)}`);
  },

  async registerLearningStrategy(payload) {
    return api.post('/api/v1/learning/strategies', payload);
  },

  async getLearningRecommendations(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/recommendations${qs ? `?${qs}` : ''}`);
  },

  async listLearningExperiences(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/experiences${qs ? `?${qs}` : ''}`);
  },

  async recordLearningExperience(payload) {
    return api.post('/api/v1/learning/experiences', payload);
  },

  async listLearningFailures(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/failures${qs ? `?${qs}` : ''}`);
  },

  async checkPreFlightWarning(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/failures/pre-flight${qs ? `?${qs}` : ''}`);
  },

  async listLearningExperiments(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/experiments${qs ? `?${qs}` : ''}`);
  },

  async createLearningExperiment(payload) {
    return api.post('/api/v1/learning/experiments', payload);
  },

  async promoteLearningStrategy(payload) {
    return api.post('/api/v1/learning/promote', payload);
  },

  async rollbackLearningStrategy(payload) {
    return api.post('/api/v1/learning/rollback', payload);
  },

  async submitLearningFeedback(payload) {
    return api.post('/api/v1/learning/feedback', payload);
  },

  async getLearningStats() {
    return api.get('/api/v1/learning/stats');
  },

  // --- Continuous Learning & Experience Consolidation Engine (Task 52) ---
  async getContinuousLearningMetrics() {
    return api.get('/api/v1/learning/continuous/metrics');
  },

  async evaluateLearningOutcome(payload) {
    return api.post('/api/v1/learning/continuous/outcomes', payload);
  },

  async extractLearningLesson(payload) {
    return api.post('/api/v1/learning/continuous/lessons', payload);
  },

  async listLearningLessons(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/continuous/lessons${qs ? `?${qs}` : ''}`);
  },

  async consolidateLearningLessons(payload) {
    return api.post('/api/v1/learning/continuous/lessons/consolidate', payload);
  },

  async runLearningReplay(payload) {
    return api.post('/api/v1/learning/continuous/replays', payload);
  },

  async registerLearningWorkflow(payload) {
    return api.post('/api/v1/learning/continuous/workflows', payload);
  },

  async listLearningWorkflows(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/continuous/workflows${qs ? `?${qs}` : ''}`);
  },

  async registerLearningHeuristic(payload) {
    return api.post('/api/v1/learning/continuous/heuristics', payload);
  },

  async listLearningHeuristics(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/learning/continuous/heuristics${qs ? `?${qs}` : ''}`);
  },

  async submitLearningCorrection(payload) {
    return api.post('/api/v1/learning/continuous/corrections', payload);
  },

  async getLearningGovernancePolicy() {
    return api.get('/api/v1/learning/continuous/governance');
  },

  // ==================================================
  // Task 44 Multi-Agent Collaboration & Collective Intelligence
  // ==================================================

  async createCollaborationSession(payload) {
    return api.post('/api/v1/collaboration/sessions', payload);
  },

  async getCollaborationSession(sessionId) {
    return api.get(`/api/v1/collaboration/sessions/${encodeURIComponent(sessionId)}`);
  },

  async registerCollaborationAgent(payload) {
    return api.post('/api/v1/collaboration/agents', payload);
  },

  async listCollaborationAgents(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/collaboration/agents${qs ? `?${qs}` : ''}`);
  },

  async createAgentContract(payload) {
    return api.post('/api/v1/collaboration/contracts', payload);
  },

  async expandAgentContract(payload) {
    return api.post('/api/v1/collaboration/contracts/expand', payload);
  },

  async getAgentContract(contractId) {
    return api.get(`/api/v1/collaboration/contracts/${encodeURIComponent(contractId)}`);
  },

  async delegateCollaborationSubtask(payload) {
    return api.post('/api/v1/collaboration/delegations', payload);
  },

  async sendAgentMessage(payload) {
    return api.post('/api/v1/collaboration/messages', payload);
  },

  async getAgentMessages(recipientId) {
    return api.get(`/api/v1/collaboration/messages/${encodeURIComponent(recipientId)}`);
  },

  async submitCollaborationEvidence(payload) {
    return api.post('/api/v1/collaboration/evidence', payload);
  },

  async listCollaborationEvidence() {
    return api.get('/api/v1/collaboration/evidence');
  },

  async createDisagreement(payload) {
    return api.post('/api/v1/collaboration/disagreements', payload);
  },

  async resolveDisagreement(payload) {
    return api.post('/api/v1/collaboration/disagreements/resolve', payload);
  },

  async checkConsensus(payload) {
    return api.post('/api/v1/collaboration/consensus', payload);
  },

  async synthesizeCollaborationFindings(payload) {
    return api.post('/api/v1/collaboration/synthesis', payload);
  },

  async triggerEmergencyStop(payload) {
    return api.post('/api/v1/collaboration/emergency-stop', payload);
  },

  async getCollaborationProvenance(sessionId) {
    return api.get(`/api/v1/collaboration/provenance/${encodeURIComponent(sessionId)}`);
  },

  // ==================================================
  // Task 45 Autonomous Execution & Long-Horizon Agency Engine
  // ==================================================

  async createAutonomousGoal(payload) {
    return api.post('/api/v1/autonomy/goals', payload);
  },

  async getAutonomousGoal(goalId) {
    return api.get(`/api/v1/autonomy/goals/${encodeURIComponent(goalId)}`);
  },

  async createAutonomousRun(payload) {
    return api.post('/api/v1/autonomy/runs', payload);
  },

  async getAutonomousRun(runId) {
    return api.get(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}`);
  },

  async controlAutonomousRun(runId, payload) {
    return api.post(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}/control`, payload);
  },

  async executeAutonomousStep(runId, payload = {}) {
    return api.post(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}/step`, payload);
  },

  async getAutonomousProgress(runId) {
    return api.get(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}/progress`);
  },

  async getAutonomousCheckpoints(runId) {
    return api.get(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}/checkpoints`);
  },

  async getAutonomousCompletion(runId) {
    return api.get(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}/completion`);
  },

  async getAutonomousWatchdog(runId) {
    return api.get(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}/watchdog`);
  },

  async postAutonomousEvent(runId, payload) {
    return api.post(`/api/v1/autonomy/runs/${encodeURIComponent(runId)}/events`, payload);
  },

  // ==================================================
  // Task 46 Perception & Environmental Awareness Engine
  // ==================================================

  async registerPerceptionSource(payload) {
    return api.post('/api/v1/perception/sources', payload);
  },

  async listPerceptionSources(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/perception/sources${qs ? `?${qs}` : ''}`);
  },

  async disablePerceptionSource(sourceId) {
    return api.post(`/api/v1/perception/sources/${encodeURIComponent(sourceId)}/disable`);
  },

  async ingestPerceptionEvent(sourceId, payload) {
    return api.post(`/api/v1/perception/sources/${encodeURIComponent(sourceId)}/events`, payload);
  },

  async getRecentObservations(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/perception/observations${qs ? `?${qs}` : ''}`);
  },

  async getRecentChanges() {
    return api.get('/api/v1/perception/changes');
  },

  async captureEnvironmentSnapshot(payload) {
    return api.post('/api/v1/perception/snapshots', payload);
  },

  async getLatestSnapshot(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/perception/snapshots/latest${qs ? `?${qs}` : ''}`);
  },

  async getLiveSituation(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/perception/situation${qs ? `?${qs}` : ''}`);
  },

  async getPerceptionHealth() {
    return api.get('/api/v1/perception/health');
  },

  // ==================================================
  // Task 47 Predictive Intelligence & Anticipation Engine
  // ==================================================

  async createPrediction(payload) {
    return api.post('/api/v1/prediction/predictions', payload);
  },

  async listPredictions(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/prediction/predictions${qs ? `?${qs}` : ''}`);
  },

  async getPrediction(predictionId) {
    return api.get(`/api/v1/prediction/predictions/${encodeURIComponent(predictionId)}`);
  },

  async evaluatePredictionOutcome(predictionId, payload) {
    return api.post(`/api/v1/prediction/predictions/${encodeURIComponent(predictionId)}/evaluate`, payload);
  },

  async createForecast(payload) {
    return api.post('/api/v1/prediction/forecasts', payload);
  },

  async issueEarlyWarning(payload) {
    return api.post('/api/v1/prediction/warnings', payload);
  },

  async listActiveWarnings() {
    return api.get('/api/v1/prediction/warnings');
  },

  async evaluatePredictedRisk(payload) {
    return api.post('/api/v1/prediction/risks', payload);
  },

  async listPredictedRisks() {
    return api.get('/api/v1/prediction/risks');
  },

  async simulateScenarios(payload) {
    return api.post('/api/v1/prediction/simulate', payload);
  },

  async evaluateCounterfactual(payload) {
    return api.post('/api/v1/prediction/counterfactual', payload);
  },

  async getCalibrationMetrics(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/prediction/calibration${qs ? `?${qs}` : ''}`);
  },

  async getPredictionHealth() {
    return api.get('/api/v1/prediction/health');
  },

  // Task 48: Intent Understanding, Goal Extraction & Safe Motivation
  async parseIntent(payload) {
    return api.post('/api/v1/intent/parse', payload);
  },

  async listIntents() {
    return api.get('/api/v1/intent/intents');
  },

  async getIntent(intentId) {
    return api.get(`/api/v1/intent/intents/${encodeURIComponent(intentId)}`);
  },

  async createGoal(payload) {
    return api.post('/api/v1/intent/goals', payload);
  },

  async listGoals(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/intent/goals${qs ? `?${qs}` : ''}`);
  },

  async answerClarification(payload) {
    return api.post('/api/v1/intent/clarify', payload);
  },

  async applyUserCorrection(payload) {
    return api.post('/api/v1/intent/correct', payload);
  },

  async revokeIntent(payload) {
    return api.post('/api/v1/intent/revoke', payload);
  },

  async getIntentGraph(intentId) {
    return api.get(`/api/v1/intent/graph/${encodeURIComponent(intentId)}`);
  },

  async analyzeTradeoffs(payload) {
    return api.post('/api/v1/intent/tradeoffs', payload);
  },

  async getIntentHealth() {
    return api.get('/api/v1/intent/health');
  },

  // Task 49: Communication & Social Intelligence
  async ingestInboundCommunication(payload) {
    return api.post('/api/v1/communication/messages/inbound', payload);
  },

  async listCommunicationThreads(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/communication/threads${qs ? `?${qs}` : ''}`);
  },

  async getCommunicationThread(threadId) {
    return api.get(`/api/v1/communication/threads/${encodeURIComponent(threadId)}`);
  },

  async generateCommunicationDraft(threadId, payload = {}) {
    return api.post(`/api/v1/communication/threads/${encodeURIComponent(threadId)}/draft`, payload);
  },

  async listCommunicationDrafts(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/communication/drafts${qs ? `?${qs}` : ''}`);
  },

  async approveCommunicationDraft(draftId, payload = {}) {
    return api.post(`/api/v1/communication/drafts/${encodeURIComponent(draftId)}/approve`, payload);
  },

  async sendCommunication(payload, isUserApproved = false) {
    return api.post(`/api/v1/communication/send?is_user_approved=${Boolean(isUserApproved)}`, payload);
  },

  async listCommunicationContacts() {
    return api.get('/api/v1/communication/contacts');
  },

  async addCommunicationContact(payload) {
    return api.post('/api/v1/communication/contacts', payload);
  },

  async listCommunicationCommitments(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/communication/commitments${qs ? `?${qs}` : ''}`);
  },

  async listCommunicationFollowups(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/communication/followups${qs ? `?${qs}` : ''}`);
  },

  async getCommunicationMetrics() {
    return api.get('/api/v1/communication/metrics');
  },

  async getCommunicationHealth() {
    return api.get('/api/v1/communication/health');
  },

  // Task 50: Personal Knowledge Graph & Relationship Memory
  async createKnowledgeNode(payload) {
    return api.post('/api/v1/knowledge-graph/nodes', payload);
  },

  async listKnowledgeNodes(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/knowledge-graph/nodes${qs ? `?${qs}` : ''}`);
  },

  async getKnowledgeNode(nodeId) {
    return api.get(`/api/v1/knowledge-graph/nodes/${encodeURIComponent(nodeId)}`);
  },

  async createKnowledgeEdge(payload) {
    return api.post('/api/v1/knowledge-graph/edges', payload);
  },

  async traverseKnowledgeGraph(payload) {
    return api.post('/api/v1/knowledge-graph/traverse', payload);
  },

  async recordKnowledgeAssertion(payload) {
    return api.post('/api/v1/knowledge-graph/assertions', payload);
  },

  async findKnowledgeAssertions(subject, params = {}) {
    const qs = new URLSearchParams({ subject, ...params }).toString();
    return api.get(`/api/v1/knowledge-graph/assertions?${qs}`);
  },

  async recordKnowledgeDecision(payload) {
    return api.post('/api/v1/knowledge-graph/decisions', payload);
  },

  async listKnowledgeDecisions(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/knowledge-graph/decisions${qs ? `?${qs}` : ''}`);
  },

  async setKnowledgePreference(payload) {
    return api.post('/api/v1/knowledge-graph/preferences', payload);
  },

  async resolveKnowledgePreference(category, params = {}) {
    const qs = new URLSearchParams({ category, ...params }).toString();
    return api.get(`/api/v1/knowledge-graph/preferences/resolve?${qs}`);
  },

  async queryKnowledgeAsOf(timestamp, params = {}) {
    const qs = new URLSearchParams({ timestamp, ...params }).toString();
    return api.get(`/api/v1/knowledge-graph/temporal/as-of?${qs}`);
  },

  async listKnowledgeContradictions(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/knowledge-graph/contradictions${qs ? `?${qs}` : ''}`);
  },

  async forgetKnowledgeEntity(payload) {
    return api.post('/api/v1/knowledge-graph/forget', payload);
  },

  async getKnowledgeGraphMetrics() {
    return api.get('/api/v1/knowledge-graph/metrics');
  },

  async getKnowledgeGraphHealth() {
    return api.get('/api/v1/knowledge-graph/health');
  },

  // Task 51: Self-Modeling & Metacognition
  async getSelfModel(userId = 'default_user') {
    return api.get(`/api/v1/metacognition/self-model?user_id=${encodeURIComponent(userId)}`);
  },

  async getSelfModelProjection(userId = 'default_user') {
    return api.get(`/api/v1/metacognition/self-model/projection?user_id=${encodeURIComponent(userId)}`);
  },

  async listCapabilities(state = null) {
    return api.get(`/api/v1/metacognition/capabilities${state ? `?state=${encodeURIComponent(state)}` : ''}`);
  },

  async listLimitations(category = null) {
    return api.get(`/api/v1/metacognition/limitations${category ? `?category=${encodeURIComponent(category)}` : ''}`);
  },

  async registerLimitation(payload) {
    return api.post('/api/v1/metacognition/limitations', payload);
  },

  async checkActionReadiness(payload) {
    return api.post('/api/v1/metacognition/readiness', payload);
  },

  async introspect(questionType, subjectOrAction = null) {
    return api.post('/api/v1/metacognition/introspect', {
      question_type: questionType,
      subject_or_action: subjectOrAction,
    });
  },

  async recordReflection(payload) {
    return api.post('/api/v1/metacognition/reflection', payload);
  },

  async getMetacognitiveMetrics() {
    return api.get('/api/v1/metacognition/metrics');
  },

  async reconcileSelfModel(payload = {}) {
    return api.post('/api/v1/metacognition/reconcile', payload);
  },

  async getMetacognitionHealth() {
    return api.get('/api/v1/metacognition/health');
  },
};

export const intentApi = {
  parseIntent: (payload) => Endpoints.parseIntent(payload),
  listIntents: () => Endpoints.listIntents(),
  getIntent: (id) => Endpoints.getIntent(id),
  createGoal: (payload) => Endpoints.createGoal(payload),
  listGoals: (params) => Endpoints.listGoals(params),
  answerClarification: (payload) => Endpoints.answerClarification(payload),
  applyUserCorrection: (payload) => Endpoints.applyUserCorrection(payload),
  revokeIntent: (payload) => Endpoints.revokeIntent(payload),
  getIntentGraph: (id) => Endpoints.getIntentGraph(id),
  analyzeTradeoffs: (payload) => Endpoints.analyzeTradeoffs(payload),
  getIntentHealth: () => Endpoints.getIntentHealth(),
};

export const communicationApi = {
  ingestInbound: (payload) => Endpoints.ingestInboundCommunication(payload),
  listThreads: (params) => Endpoints.listCommunicationThreads(params),
  getThread: (id) => Endpoints.getCommunicationThread(id),
  generateDraft: (id, payload) => Endpoints.generateCommunicationDraft(id, payload),
  listDrafts: (params) => Endpoints.listCommunicationDrafts(params),
  approveDraft: (id, payload) => Endpoints.approveCommunicationDraft(id, payload),
  send: (payload, approved) => Endpoints.sendCommunication(payload, approved),
  listContacts: () => Endpoints.listCommunicationContacts(),
  addContact: (payload) => Endpoints.addCommunicationContact(payload),
  listCommitments: (params) => Endpoints.listCommunicationCommitments(params),
  listFollowups: (params) => Endpoints.listCommunicationFollowups(params),
  getMetrics: () => Endpoints.getCommunicationMetrics(),
  getHealth: () => Endpoints.getCommunicationHealth(),
};

export const knowledgeGraphApi = {
  createNode: (payload) => Endpoints.createKnowledgeNode(payload),
  listNodes: (params) => Endpoints.listKnowledgeNodes(params),
  getNode: (id) => Endpoints.getKnowledgeNode(id),
  createEdge: (payload) => Endpoints.createKnowledgeEdge(payload),
  traverse: (payload) => Endpoints.traverseKnowledgeGraph(payload),
  recordAssertion: (payload) => Endpoints.recordKnowledgeAssertion(payload),
  findAssertions: (subject, params) => Endpoints.findKnowledgeAssertions(subject, params),
  recordDecision: (payload) => Endpoints.recordKnowledgeDecision(payload),
  listDecisions: (params) => Endpoints.listKnowledgeDecisions(params),
  setPreference: (payload) => Endpoints.setKnowledgePreference(payload),
  resolvePreference: (category, params) => Endpoints.resolveKnowledgePreference(category, params),
  queryAsOf: (ts, params) => Endpoints.queryKnowledgeAsOf(ts, params),
  listContradictions: (params) => Endpoints.listKnowledgeContradictions(params),
  forgetEntity: (payload) => Endpoints.forgetKnowledgeEntity(payload),
  getMetrics: () => Endpoints.getKnowledgeGraphMetrics(),
  getHealth: () => Endpoints.getKnowledgeGraphHealth(),
};

export const metacognitionApi = {
  getSelfModel: (userId) => Endpoints.getSelfModel(userId),
  getProjection: (userId) => Endpoints.getSelfModelProjection(userId),
  listCapabilities: (state) => Endpoints.listCapabilities(state),
  listLimitations: (category) => Endpoints.listLimitations(category),
  registerLimitation: (payload) => Endpoints.registerLimitation(payload),
  checkReadiness: (payload) => Endpoints.checkActionReadiness(payload),
  introspect: (type, subj) => Endpoints.introspect(type, subj),
  recordReflection: (payload) => Endpoints.recordReflection(payload),
  getMetrics: () => Endpoints.getMetacognitiveMetrics(),
  reconcile: (payload) => Endpoints.reconcileSelfModel(payload),
  getHealth: () => Endpoints.getMetacognitionHealth(),
};

export const continuousLearningApi = {
  getMetrics: () => Endpoints.getContinuousLearningMetrics(),
  evaluateOutcome: (payload) => Endpoints.evaluateLearningOutcome(payload),
  extractLesson: (payload) => Endpoints.extractLearningLesson(payload),
  listLessons: (params) => Endpoints.listLearningLessons(params),
  consolidateLessons: (payload) => Endpoints.consolidateLearningLessons(payload),
  runReplay: (payload) => Endpoints.runLearningReplay(payload),
  registerWorkflow: (payload) => Endpoints.registerLearningWorkflow(payload),
  listWorkflows: (params) => Endpoints.listLearningWorkflows(params),
  registerHeuristic: (payload) => Endpoints.registerLearningHeuristic(payload),
  listHeuristics: (params) => Endpoints.listLearningHeuristics(params),
  submitCorrection: (payload) => Endpoints.submitLearningCorrection(payload),
  getGovernancePolicy: () => Endpoints.getLearningGovernancePolicy(),
};

export const endpoints = Endpoints;



