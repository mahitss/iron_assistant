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

  // --- Continuous Learning ---
  async getContinuousLearningMetrics() {
    return api.get('/api/v1/learning/metrics');
  },
  async evaluateLearningOutcome(payload = {}) {
    return api.post('/api/v1/learning/evaluate', payload);
  },
  async extractLearningLesson(payload = {}) {
    return api.post('/api/v1/learning/lessons/extract', payload);
  },
  async listLearningLessons(params = {}) {
    return api.get('/api/v1/learning/lessons', params);
  },
  async consolidateLearningLessons(payload = {}) {
    return api.post('/api/v1/learning/lessons/consolidate', payload);
  },
  async runLearningReplay(payload = {}) {
    return api.post('/api/v1/learning/replay', payload);
  },
  async registerLearningWorkflow(payload = {}) {
    return api.post('/api/v1/learning/workflows', payload);
  },
  async listLearningWorkflows(params = {}) {
    return api.get('/api/v1/learning/workflows', params);
  },
  async registerLearningHeuristic(payload = {}) {
    return api.post('/api/v1/learning/heuristics', payload);
  },
  async listLearningHeuristics(params = {}) {
    return api.get('/api/v1/learning/heuristics', params);
  },
  async submitLearningCorrection(payload = {}) {
    return api.post('/api/v1/learning/feedback/correction', payload);
  },
  async getLearningGovernancePolicy() {
    return api.get('/api/v1/learning/governance/policy');
  },

  // --- Executive Memory & Long-Horizon Context ---
  async queryExecutiveContinuity(payload = {}) {
    return api.post('/api/v1/executive-memory/query', payload);
  },
  async getExecutiveState() {
    return api.get('/api/v1/executive-memory/state');
  },
  async synthesizeExecutiveState(payload = {}) {
    return api.post('/api/v1/executive-memory/state/synthesize', payload);
  },
  async listExecutiveTimeline(params = {}) {
    return api.get('/api/v1/executive-memory/timeline', params);
  },
  async recordExecutiveTimelineEvent(payload = {}) {
    return api.post('/api/v1/executive-memory/timeline/events', payload);
  },
  async reconstructExecutiveAsOf(params = {}) {
    return api.get('/api/v1/executive-memory/timeline/as-of', params);
  },
  async listExecutiveOpenLoops(params = {}) {
    return api.get('/api/v1/executive-memory/open-loops', params);
  },
  async createExecutiveOpenLoop(payload = {}) {
    return api.post('/api/v1/executive-memory/open-loops', payload);
  },
  async updateExecutiveOpenLoopStatus(loopId, payload = {}) {
    return api.patch(`/api/v1/executive-memory/open-loops/${loopId}/status`, payload);
  },
  async closeExecutiveOpenLoop(loopId, payload = {}) {
    return api.post(`/api/v1/executive-memory/open-loops/${loopId}/close`, payload);
  },
  async listExecutiveBlockers(params = {}) {
    return api.get('/api/v1/executive-memory/blockers', params);
  },
  async createExecutiveBlocker(payload = {}) {
    return api.post('/api/v1/executive-memory/blockers', payload);
  },
  async resolveExecutiveBlocker(blockerId, payload = {}) {
    return api.post(`/api/v1/executive-memory/blockers/${blockerId}/resolve`, payload);
  },
  async listExecutiveMilestones(params = {}) {
    return api.get('/api/v1/executive-memory/milestones', params);
  },
  async createExecutiveMilestone(payload = {}) {
    return api.post('/api/v1/executive-memory/milestones', payload);
  },
  async achieveExecutiveMilestone(milestoneId, payload = {}) {
    return api.post(`/api/v1/executive-memory/milestones/${milestoneId}/achieve`, payload);
  },
  async getExecutiveBrief(projectId) {
    return api.get(`/api/v1/executive-memory/briefs/${projectId}`);
  },
  async generateExecutiveBrief(projectId, payload = {}) {
    return api.post(`/api/v1/executive-memory/briefs/${projectId}`, payload);
  },
  async getExecutiveNextActions(params = {}) {
    return api.get('/api/v1/executive-memory/next-actions', params);
  },
  async createExecutiveCheckpoint(payload = {}) {
    return api.post('/api/v1/executive-memory/checkpoints', payload);
  },
  async resumeExecutiveCheckpoint(checkpointId, payload = {}) {
    return api.post(`/api/v1/executive-memory/checkpoints/${checkpointId}/resume`, payload);
  },
  async reconcileExecutiveState(payload = {}) {
    return api.post('/api/v1/executive-memory/reconcile', payload);
  },
  async getExecutiveMemoryMetrics() {
    return api.get('/api/v1/executive-memory/metrics');
  },

  // --- Environmental Intelligence & Digital Twin (Task 54) ---
  async getDigitalTwin(scope = 'SYSTEM', scopeId = null) {
    const params = new URLSearchParams({ scope });
    if (scopeId) params.append('scope_id', scopeId);
    return api.get(`/api/v1/environment/twin?${params.toString()}`);
  },

  async registerEnvironmentNode(payload) {
    return api.post('/api/v1/environment/nodes', payload);
  },

  async registerEnvironmentEdge(payload) {
    return api.post('/api/v1/environment/edges', payload);
  },

  async recordEnvironmentHealth(payload) {
    return api.post('/api/v1/environment/health', payload);
  },

  async recordEnvironmentChange(payload) {
    return api.post('/api/v1/environment/changes', payload);
  },

  async recordEnvironmentDrift(payload) {
    return api.post('/api/v1/environment/drifts', payload);
  },

  async createEnvironmentSnapshot(scope = 'SYSTEM', scopeId = null) {
    const params = new URLSearchParams({ scope });
    if (scopeId) params.append('scope_id', scopeId);
    return api.post(`/api/v1/environment/snapshots?${params.toString()}`);
  },

  async getEnvironmentStateAsOf(asOf, scope = 'SYSTEM', scopeId = null) {
    const params = new URLSearchParams({ as_of: asOf, scope });
    if (scopeId) params.append('scope_id', scopeId);
    return api.get(`/api/v1/environment/as-of?${params.toString()}`);
  },

  async createEnvironmentIncident(payload) {
    return api.post('/api/v1/environment/incidents', payload);
  },

  async simulateEnvironmentWhatIf(payload) {
    return api.post('/api/v1/environment/what-if', payload);
  },

  async proposeRemediationPlan(payload) {
    return api.post('/api/v1/environment/remediation/propose', payload);
  },

  async executeAutoHealing(payload) {
    return api.post('/api/v1/environment/remediation/auto-heal', payload);
  },

  async getEnvironmentSummary(scope = 'SYSTEM') {
    return api.get(`/api/v1/environment/summary?scope=${encodeURIComponent(scope)}`);
  },

  async getEnvironmentContext(query, scope = 'SYSTEM') {
    return api.get(`/api/v1/environment/context?query=${encodeURIComponent(query)}&scope=${encodeURIComponent(scope)}`);
  },

  async getEnvironmentDependents(nodeId, scope = 'SYSTEM') {
    return api.get(`/api/v1/environment/topology/dependents/${encodeURIComponent(nodeId)}?scope=${encodeURIComponent(scope)}`);
  },

  async getEnvironmentDependencies(nodeId, scope = 'SYSTEM') {
    return api.get(`/api/v1/environment/topology/dependencies/${encodeURIComponent(nodeId)}?scope=${encodeURIComponent(scope)}`);
  },

  async getEnvironmentUnhealthy(scope = 'SYSTEM') {
    return api.get(`/api/v1/environment/topology/unhealthy?scope=${encodeURIComponent(scope)}`);
  },

  async getEnvironmentProduction() {
    return api.get('/api/v1/environment/topology/production');
  },

  // --- Causal Reasoning & Causal Graph (Task 55) ---
  async getCausalGraph(graphId = 'system_default') {
    return api.get(`/api/v1/causal/graph?graph_id=${encodeURIComponent(graphId)}`);
  },

  async addCausalNode(payload) {
    return api.post('/api/v1/causal/nodes', payload);
  },

  async addCausalEdge(payload) {
    return api.post('/api/v1/causal/edges', payload);
  },

  async analyzeCausalRootCause(payload) {
    return api.post('/api/v1/causal/analyze', payload);
  },

  async getCausalAnalysis(incidentId) {
    return api.get(`/api/v1/causal/analysis/${encodeURIComponent(incidentId)}`);
  },

  async getCausalExplanation(incidentId) {
    return api.get(`/api/v1/causal/explanation/${encodeURIComponent(incidentId)}`);
  },

  async askCausalQuestion(payload) {
    return api.post('/api/v1/causal/question', payload);
  },

  async proposeCausalIntervention(payload) {
    return api.post('/api/v1/causal/interventions/propose', payload);
  },

  async evaluateCausalIntervention(interventionId, payload) {
    return api.post(`/api/v1/causal/interventions/${encodeURIComponent(interventionId)}/evaluate`, payload);
  },

  async evaluateCausalCounterfactual(payload) {
    return api.post('/api/v1/causal/counterfactuals/evaluate', payload);
  },

  async detectCausalFallacies(payload) {
    return api.post('/api/v1/causal/fallacies/detect', payload);
  },

  async getCausalBlastRadius(serviceName) {
    return api.get(`/api/v1/causal/blast-radius/${encodeURIComponent(serviceName)}`);
  },

  // --- Simulation & Counterfactual Planning (Task 56) ---
  async captureSimulationSnapshot(payload = {}) {
    return api.post('/api/v1/simulation/snapshots', payload);
  },

  async listSimulationSnapshots() {
    return api.get('/api/v1/simulation/snapshots');
  },

  async getSimulationSnapshot(snapshotId) {
    return api.get(`/api/v1/simulation/snapshots/${encodeURIComponent(snapshotId)}`);
  },

  async createSimulationScenario(payload) {
    return api.post('/api/v1/simulation/scenarios', payload);
  },

  async listSimulationScenarios(baselineSnapshotId = null) {
    const url = baselineSnapshotId
      ? `/api/v1/simulation/scenarios?baseline_snapshot_id=${encodeURIComponent(baselineSnapshotId)}`
      : '/api/v1/simulation/scenarios';
    return api.get(url);
  },

  async getSimulationScenario(scenarioId) {
    return api.get(`/api/v1/simulation/scenarios/${encodeURIComponent(scenarioId)}`);
  },

  async runSimulation(payload) {
    return api.post('/api/v1/simulation/run', payload);
  },

  async listSimulationRuns() {
    return api.get('/api/v1/simulation/runs');
  },

  async getSimulationRun(simulationId) {
    return api.get(`/api/v1/simulation/runs/${encodeURIComponent(simulationId)}`);
  },

  async compareSimulations(payload) {
    return api.post('/api/v1/simulation/compare', payload);
  },

  async rankSimulations(payload) {
    return api.post('/api/v1/simulation/rank', payload);
  },

  async exploreCounterfactual(payload) {
    return api.post('/api/v1/simulation/counterfactual', payload);
  },

  async runMonteCarlo(payload) {
    return api.post('/api/v1/simulation/monte-carlo', payload);
  },

  async replaySimulation(payload) {
    return api.post('/api/v1/simulation/replay', payload);
  },

  async evaluateExecutionGate(payload) {
    return api.post('/api/v1/simulation/gates/evaluate', payload);
  },

  async recordSimulationCalibration(payload) {
    return api.post('/api/v1/simulation/calibrate', payload);
  },

  async getSimulationCalibrationReport(metricName) {
    return api.get(`/api/v1/simulation/calibrations/report?metric_name=${encodeURIComponent(metricName)}`);
  },

  // --- Executive Decision Engine (Task 57) ---
  async analyzeDecision(payload) {
    return api.post('/api/v1/decision/analyze', payload);
  },

  async listDecisions(limit = 50) {
    return api.get(`/api/v1/decision?limit=${limit}`);
  },

  async getDecision(decisionId) {
    return api.get(`/api/v1/decision/${encodeURIComponent(decisionId)}`);
  },

  async selectDecisionOption(decisionId, payload) {
    return api.post(`/api/v1/decision/${encodeURIComponent(decisionId)}/select`, payload);
  },

  async approveDecision(decisionId, payload) {
    return api.post(`/api/v1/decision/${encodeURIComponent(decisionId)}/approve`, payload);
  },

  async revalidateDecision(decisionId) {
    return api.post(`/api/v1/decision/${encodeURIComponent(decisionId)}/revalidate`, {});
  },

  async recordDecisionOutcome(decisionId, payload) {
    return api.post(`/api/v1/decision/${encodeURIComponent(decisionId)}/outcome`, payload);
  },

  async getDecisionOutcome(decisionId) {
    return api.get(`/api/v1/decision/${encodeURIComponent(decisionId)}/outcome`);
  },

  async getDecisionExplanation(decisionId, query = 'why this option') {
    return api.get(`/api/v1/decision/${encodeURIComponent(decisionId)}/explanation?query=${encodeURIComponent(query)}`);
  },

  async getDecisionAsOf(decisionId) {
    return api.get(`/api/v1/decision/${encodeURIComponent(decisionId)}/as-of`);
  },

  async getDecisionCalibrationAnalytics() {
    return api.get('/api/v1/decision/analytics/calibration');
  },

  // --- Task 58: Strategic Planning Engine ---
  async createPlan(payload) {
    return api.post('/api/v1/planning/plans', payload);
  },

  async listPlans() {
    return api.get('/api/v1/planning/plans');
  },

  async getPlan(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}`);
  },

  async validatePlan(planId, payload = {}) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/validate`, payload);
  },

  async analyzePlan(planId) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/analyze`);
  },

  async startPlan(planId, payload = {}) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/start`, payload);
  },

  async pausePlan(planId, payload = {}) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/pause`, payload);
  },

  async resumePlan(planId, payload = {}) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/resume`, payload);
  },

  async cancelPlan(planId, payload = {}) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/cancel`, payload);
  },

  async replan(planId, payload) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/replan`, payload);
  },

  async getPlanProgress(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}/progress`);
  },

  async getPlanTimeline(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}/timeline`);
  },

  async getPlanDependencies(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}/dependencies`);
  },

  async getPlanRisks(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}/risks`);
  },

  async getPlanOutcomes(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}/outcomes`);
  },

  async recordPlanOutcome(planId, payload) {
    return api.post(`/api/v1/planning/plans/${encodeURIComponent(planId)}/outcomes`, payload);
  },

  async getExecutionProposal(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}/proposal`);
  },

  async getPlanAudit(planId) {
    return api.get(`/api/v1/planning/plans/${encodeURIComponent(planId)}/audit`);
  },

  // --- Task 59: Resource & Capability Orchestration Engine ---
  async analyzeOrchestration(payload) {
    return api.post('/api/v1/orchestration/analyze', payload);
  },

  async createOrchestration(payload) {
    return api.post('/api/v1/orchestration', payload);
  },

  async listCapabilities(environment = null, status = null) {
    let q = [];
    if (environment) q.push(`environment=${encodeURIComponent(environment)}`);
    if (status) q.push(`status=${encodeURIComponent(status)}`);
    const qs = q.length ? `?${q.join('&')}` : '';
    return api.get(`/api/v1/orchestration/catalog/capabilities${qs}`);
  },

  async listResources(environment = null, resourceType = null) {
    let q = [];
    if (environment) q.push(`environment=${encodeURIComponent(environment)}`);
    if (resourceType) q.push(`resource_type=${encodeURIComponent(resourceType)}`);
    const qs = q.length ? `?${q.join('&')}` : '';
    return api.get(`/api/v1/orchestration/catalog/resources${qs}`);
  },

  async reserveResource(payload) {
    return api.post('/api/v1/orchestration/resources/reserve', payload);
  },

  async releaseReservation(reservationId) {
    return api.post('/api/v1/orchestration/resources/release', { reservation_id: reservationId });
  },

  async listOrchestrations(status = null, limit = 50) {
    let q = `?limit=${limit}`;
    if (status) q += `&status=${encodeURIComponent(status)}`;
    return api.get(`/api/v1/orchestration/list${q}`);
  },

  async getOrchestration(orchestrationId) {
    return api.get(`/api/v1/orchestration/${encodeURIComponent(orchestrationId)}`);
  },

  async getOrchestrationAssignments(orchestrationId) {
    return api.get(`/api/v1/orchestration/${encodeURIComponent(orchestrationId)}/assignments`);
  },

  async getOrchestrationTopology(orchestrationId) {
    return api.get(`/api/v1/orchestration/${encodeURIComponent(orchestrationId)}/topology`);
  },

  async revalidateOrchestration(orchestrationId, payload = {}) {
    return api.post(`/api/v1/orchestration/${encodeURIComponent(orchestrationId)}/revalidate`, payload);
  },

  async failoverOrchestration(orchestrationId, payload) {
    return api.post(`/api/v1/orchestration/${encodeURIComponent(orchestrationId)}/failover`, payload);
  },

  async getOrchestrationHealth(orchestrationId) {
    return api.get(`/api/v1/orchestration/${encodeURIComponent(orchestrationId)}/health`);
  },

  async explainOrchestrationTask(taskId) {
    return api.get(`/api/v1/orchestration/explain/${encodeURIComponent(taskId)}`);
  },

  async getOrchestrationAudit(orchestrationId = null, limit = 100) {
    let q = `?limit=${limit}`;
    if (orchestrationId) q += `&orchestration_id=${encodeURIComponent(orchestrationId)}`;
    return api.get(`/api/v1/orchestration/audit/trail${q}`);
  },

  // --- Task 60: Real-Time Situational Awareness & Event Correlation Engine ---
  async ingestSituationEvent(payload) {
    return api.post('/api/v1/situations/events', payload);
  },

  async listSituations(environment = null, status = null) {
    let q = [];
    if (environment) q.push(`environment=${encodeURIComponent(environment)}`);
    if (status) q.push(`status=${encodeURIComponent(status)}`);
    const qs = q.length ? `?${q.join('&')}` : '';
    return api.get(`/api/v1/situations${qs}`);
  },

  async getSituation(situationId) {
    return api.get(`/api/v1/situations/${encodeURIComponent(situationId)}`);
  },

  async getSituationTimeline(situationId) {
    return api.get(`/api/v1/situations/${encodeURIComponent(situationId)}/timeline`);
  },

  async getSituationImpact(situationId) {
    return api.get(`/api/v1/situations/${encodeURIComponent(situationId)}/impact`);
  },

  async getSituationHypotheses(situationId) {
    return api.get(`/api/v1/situations/${encodeURIComponent(situationId)}/hypotheses`);
  },

  async resolveSituation(situationId, payload) {
    return api.post(`/api/v1/situations/${encodeURIComponent(situationId)}/resolve`, payload);
  },

  async escalateSituation(situationId, payload) {
    return api.post(`/api/v1/situations/${encodeURIComponent(situationId)}/escalate`, payload);
  },

  async getAttentionFeed() {
    return api.get('/api/v1/situations/attention/feed');
  },

  async listSignalBaselines(environment = null) {
    let q = environment ? `?environment=${encodeURIComponent(environment)}` : '';
    return api.get(`/api/v1/situations/baselines/catalog${q}`);
  },

  async getSituationAudit(situationId = null, limit = 100) {
    let q = `?limit=${limit}`;
    if (situationId) q += `&situation_id=${encodeURIComponent(situationId)}`;
    return api.get(`/api/v1/situations/audit/trail${q}`);
  },

  // --- Task 61: Incident Response & Recovery Autonomy Engine ---
  async createIncidentFromSituation(payload) {
    return api.post('/api/v1/incidents/from-situation', payload);
  },

  async listIncidents(environment = null, status = null) {
    let q = [];
    if (environment) q.push(`environment=${encodeURIComponent(environment)}`);
    if (status) q.push(`status=${encodeURIComponent(status)}`);
    const qs = q.length ? `?${q.join('&')}` : '';
    return api.get(`/api/v1/incidents${qs}`);
  },

  async getIncident(incidentId) {
    return api.get(`/api/v1/incidents/${encodeURIComponent(incidentId)}`);
  },

  async triageIncident(incidentId, payload) {
    return api.post(`/api/v1/incidents/${encodeURIComponent(incidentId)}/triage`, payload);
  },

  async addIncidentEvidence(incidentId, payload) {
    return api.post(`/api/v1/incidents/${encodeURIComponent(incidentId)}/evidence`, payload);
  },

  async selectIncidentOption(incidentId, optionId, payload = {}) {
    return api.post(`/api/v1/incidents/${encodeURIComponent(incidentId)}/options/${encodeURIComponent(optionId)}/select`, payload);
  },

  async approveIncidentAction(incidentId, payload) {
    return api.post(`/api/v1/incidents/${encodeURIComponent(incidentId)}/actions/approve`, payload);
  },

  async verifyRecoveryCheckpoint(incidentId, payload) {
    return api.post(`/api/v1/incidents/${encodeURIComponent(incidentId)}/checkpoints/verify`, payload);
  },

  async resolveIncident(incidentId, payload) {
    return api.post(`/api/v1/incidents/${encodeURIComponent(incidentId)}/resolve`, payload);
  },

  async reopenIncident(incidentId, payload) {
    return api.post(`/api/v1/incidents/${encodeURIComponent(incidentId)}/reopen`, payload);
  },

  async getIncidentPostmortem(incidentId) {
    return api.get(`/api/v1/incidents/${encodeURIComponent(incidentId)}/postmortem`);
  },

  async getIncidentAudit(incidentId = null, limit = 100) {
    let q = `?limit=${limit}`;
    if (incidentId) q += `&incident_id=${encodeURIComponent(incidentId)}`;
    return api.get(`/api/v1/incidents/audit/trail${q}`);
  },

  // --- Task 62: Continuous Self-Optimization & Adaptive Control Engine ---
  async evaluateOptimization(payload) {
    return api.post('/api/v1/optimization/evaluate', payload);
  },

  async listOptimizationRecommendations() {
    return api.get('/api/v1/optimization/recommendations');
  },

  async getOptimizationRecommendation(recommendationId) {
    return api.get(`/api/v1/optimization/recommendations/${encodeURIComponent(recommendationId)}`);
  },

  async approveOptimizationRecommendation(recommendationId, payload) {
    return api.post(`/api/v1/optimization/recommendations/${encodeURIComponent(recommendationId)}/approve`, payload);
  },

  async listOptimizationExperiments(status = null) {
    let q = status ? `?status=${encodeURIComponent(status)}` : '';
    return api.get(`/api/v1/optimization/experiments${q}`);
  },

  async createOptimizationExperiment(payload) {
    return api.post('/api/v1/optimization/experiments', payload);
  },

  async getOptimizationExperiment(experimentId) {
    return api.get(`/api/v1/optimization/experiments/${encodeURIComponent(experimentId)}`);
  },

  async approveOptimizationExperiment(experimentId, approver = 'ADMIN') {
    return api.post(`/api/v1/optimization/experiments/${encodeURIComponent(experimentId)}/approve?approver=${encodeURIComponent(approver)}`);
  },

  async startOptimizationExperiment(experimentId) {
    return api.post(`/api/v1/optimization/experiments/${encodeURIComponent(experimentId)}/start`);
  },

  async deployOptimizationCanary(payload) {
    return api.post('/api/v1/optimization/canary/deploy', payload);
  },

  async verifyOptimizationCanary(canaryId, isVerified = true, advanceToFull = true) {
    return api.post(`/api/v1/optimization/canary/${encodeURIComponent(canaryId)}/verify?is_verified=${isVerified}&advance_to_full=${advanceToFull}`);
  },

  async rollbackOptimizationCanary(canaryId, reason = 'Rollback requested', actor = 'OPERATOR') {
    return api.post(`/api/v1/optimization/canary/${encodeURIComponent(canaryId)}/rollback?reason=${encodeURIComponent(reason)}&actor=${encodeURIComponent(actor)}`);
  },

  async listOptimizationChangeSets() {
    return api.get('/api/v1/optimization/change-sets');
  },

  async ingestOptimizationMeasurement(payload) {
    return api.post('/api/v1/optimization/metrics/measurements', payload);
  },

  async getOptimizationMetrics() {
    return api.get('/api/v1/optimization/metrics');
  },

  async listOptimizationBaselines() {
    return api.get('/api/v1/optimization/baselines');
  },

  async listOptimizationDrift() {
    return api.get('/api/v1/optimization/drift');
  },

  async listOptimizationCalibration() {
    return api.get('/api/v1/optimization/calibration');
  },

  async getOptimizationAudit(changeSetId = null, experimentId = null, limit = 100) {
    let q = [`limit=${limit}`];
    if (changeSetId) q.push(`change_set_id=${encodeURIComponent(changeSetId)}`);
    if (experimentId) q.push(`experiment_id=${encodeURIComponent(experimentId)}`);
    return api.get(`/api/v1/optimization/audit/trail?${q.join('&')}`);
  },

  async toggleOptimizationKillSwitch(payload) {
    return api.post('/api/v1/optimization/kill-switch', payload);
  },

  // --- Knowledge Synthesis & Research Intelligence (Task 63) ---
  async startResearch(payload) {
    return api.post('/api/v1/research', payload);
  },

  async listResearchSessions(limit = 50) {
    return api.get(`/api/v1/research?limit=${limit}`);
  },

  async getResearch(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}`);
  },

  async getResearchSources(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}/sources`);
  },

  async getResearchClaims(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}/claims`);
  },

  async getResearchEvidence(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}/evidence`);
  },

  async getResearchConflicts(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}/conflicts`);
  },

  async getResearchGaps(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}/gaps`);
  },

  async getResearchTimeline(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}/timeline`);
  },

  async continueResearch(sessionId, followUpQuestion) {
    return api.post(`/api/v1/research/${encodeURIComponent(sessionId)}/continue?follow_up_question=${encodeURIComponent(followUpQuestion)}`);
  },

  async verifyResearchClaim(sessionId, payload) {
    return api.post(`/api/v1/research/${encodeURIComponent(sessionId)}/verify`, payload);
  },

  async ingestResearchDocument(payload) {
    return api.post('/api/v1/research/documents', payload);
  },

  async getResearchClaim(claimId) {
    return api.get(`/api/v1/research/claims/${encodeURIComponent(claimId)}`);
  },

  async getResearchSource(sourceId) {
    return api.get(`/api/v1/research/sources/${encodeURIComponent(sourceId)}`);
  },

  async retractResearchSource(sourceId, reason = 'Retracted by publisher') {
    return api.post(`/api/v1/research/sources/${encodeURIComponent(sourceId)}/retract?reason=${encodeURIComponent(reason)}`);
  },

  async getResearchDecisionPackage(sessionId) {
    return api.get(`/api/v1/research/${encodeURIComponent(sessionId)}/decision-package`);
  },

  async getResearchKnowledgeChanges(limit = 100) {
    return api.get(`/api/v1/research/knowledge/changes?limit=${limit}`);
  },

  async getResearchAudit(sessionId = null, sourceId = null, claimId = null, limit = 100) {
    let q = [`limit=${limit}`];
    if (sessionId) q.push(`session_id=${encodeURIComponent(sessionId)}`);
    if (sourceId) q.push(`source_id=${encodeURIComponent(sourceId)}`);
    if (claimId) q.push(`claim_id=${encodeURIComponent(claimId)}`);
    return api.get(`/api/v1/research/audit/trail?${q.join('&')}`);
  },

  // --- Task 64 Collective Intelligence & Swarm Reasoning ---
  async createSwarmSession(payload) {
    return api.post('/api/v1/swarm/', payload);
  },

  async listSwarmSessions(limit = 20) {
    return api.get(`/api/v1/swarm/?limit=${limit}`);
  },

  async getSwarmSession(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}`);
  },

  async getSwarmAgents(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}/agents`);
  },

  async getSwarmTasks(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}/tasks`);
  },

  async getSwarmResults(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}/results`);
  },

  async getSwarmReviews(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}/reviews`);
  },

  async getSwarmDisagreements(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}/disagreements`);
  },

  async getSwarmMinorities(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}/minorities`);
  },

  async getSwarmTimeline(swarmId) {
    return api.get(`/api/v1/swarm/${encodeURIComponent(swarmId)}/timeline`);
  },

  async pauseSwarm(swarmId) {
    return api.post(`/api/v1/swarm/${encodeURIComponent(swarmId)}/pause`, {});
  },

  async resumeSwarm(swarmId) {
    return api.post(`/api/v1/swarm/${encodeURIComponent(swarmId)}/resume`, {});
  },

  async cancelSwarm(swarmId, payload = {}) {
    return api.post(`/api/v1/swarm/${encodeURIComponent(swarmId)}/cancel`, payload);
  },

  async synthesizeSwarm(swarmId) {
    return api.post(`/api/v1/swarm/${encodeURIComponent(swarmId)}/synthesize`, {});
  },

  async verifySwarm(swarmId, notes = null) {
    const q = notes ? `?notes=${encodeURIComponent(notes)}` : '';
    return api.post(`/api/v1/swarm/${encodeURIComponent(swarmId)}/verify${q}`, {});
  },

  async getSwarmAudit(swarmId = null, limit = 50) {
    const q = swarmId ? `?swarm_id=${encodeURIComponent(swarmId)}&limit=${limit}` : `?limit=${limit}`;
    return api.get(`/api/v1/swarm/audit/trail${q}`);
  },

  async getSwarmHealth() {
    return api.get('/api/v1/swarm/health');
  },

  // --- Task 65: Autonomous World Model & Long-Horizon Foresight Engine ---
  async getWorldModelOverview() {
    return api.get('/api/v1/world-model');
  },

  async queryWorldModel(payload) {
    return api.post('/api/v1/world-model/query', payload);
  },

  async listWorldEntities(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/world-model/entities${qs ? `?${qs}` : ''}`);
  },

  async getWorldEntity(entityId) {
    return api.get(`/api/v1/world-model/entities/${encodeURIComponent(entityId)}`);
  },

  async listWorldRelationships(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/api/v1/world-model/relationships${qs ? `?${qs}` : ''}`);
  },

  async getWorldDiff(historicalTimestamp = null) {
    const qs = historicalTimestamp ? `?historical_timestamp=${encodeURIComponent(historicalTimestamp)}` : '';
    return api.get(`/api/v1/world-model/diff${qs}`);
  },

  async reassessWorldModel(payload = {}) {
    return api.post('/api/v1/world-model/reassess', payload);
  },

  async createForecast(payload) {
    return api.post('/api/v1/foresight/forecast', payload);
  },

  async listForecasts(horizon = null) {
    const qs = horizon ? `?horizon=${encodeURIComponent(horizon)}` : '';
    return api.get(`/api/v1/foresight/forecasts${qs}`);
  },

  async getForecast(forecastId) {
    return api.get(`/api/v1/foresight/forecast/${encodeURIComponent(forecastId)}`);
  },

  async getForecastEvidence(forecastId) {
    return api.get(`/api/v1/foresight/forecast/${encodeURIComponent(forecastId)}/evidence`);
  },

  async getForecastAssumptions(forecastId) {
    return api.get(`/api/v1/foresight/forecast/${encodeURIComponent(forecastId)}/assumptions`);
  },

  async getForecastScenarios(forecastId) {
    return api.get(`/api/v1/foresight/forecast/${encodeURIComponent(forecastId)}/scenarios`);
  },

  async getForecastOutcomes(forecastId) {
    return api.get(`/api/v1/foresight/forecast/${encodeURIComponent(forecastId)}/outcomes`);
  },

  async createScenario(payload) {
    return api.post('/api/v1/foresight/scenario', payload);
  },

  async listScenarios(scenarioType = null) {
    const qs = scenarioType ? `?scenario_type=${encodeURIComponent(scenarioType)}` : '';
    return api.get(`/api/v1/foresight/scenarios${qs}`);
  },

  async listStrategicRisks() {
    return api.get('/api/v1/foresight/risks');
  },

  async listStrategicOpportunities() {
    return api.get('/api/v1/foresight/opportunities');
  },

  async listEarlyWarnings() {
    return api.get('/api/v1/foresight/early-warnings');
  },

  async getForesightAudit(limit = 50) {
    return api.get(`/api/v1/foresight/audit/trail?limit=${limit}`);
  },

  async getForesightHealth() {
    return api.get('/api/v1/foresight/health');
  },

  // --- Task 66: Autonomous Goal Management & Self-Directed Mission Engine ---
  async createMission(payload, isHumanApproved = false) {
    return api.post(`/api/v1/missions/?is_human_approved=${Boolean(isHumanApproved)}`, payload);
  },

  async listMissions(tenantId = 'default') {
    return api.get(`/api/v1/missions/?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionOverview(tenantId = 'default') {
    return api.get(`/api/v1/missions/overview?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMission(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async startMission(missionId, tenantId = 'default') {
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/start?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async pauseMission(missionId, reason = '', tenantId = 'default') {
    const qs = reason ? `&reason=${encodeURIComponent(reason)}` : '';
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/pause?tenant_id=${encodeURIComponent(tenantId)}${qs}`);
  },

  async resumeMission(missionId, tenantId = 'default') {
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/resume?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async cancelMission(missionId, reason = '', tenantId = 'default') {
    const qs = reason ? `&reason=${encodeURIComponent(reason)}` : '';
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/cancel?tenant_id=${encodeURIComponent(tenantId)}${qs}`);
  },

  async replanMission(missionId, reason = '', tenantId = 'default') {
    const qs = reason ? `&reason=${encodeURIComponent(reason)}` : '';
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/replan?tenant_id=${encodeURIComponent(tenantId)}${qs}`);
  },

  async executeSupervisoryCycle(missionId, payload = {}, tenantId = 'default') {
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/cycle?tenant_id=${encodeURIComponent(tenantId)}`, payload);
  },

  async completeMission(missionId, tenantId = 'default') {
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/complete?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionAuditTrail(missionId) {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/audit`);
  },

  async verifyMissionAuditChain() {
    return api.get('/api/v1/missions/audit/verify');
  },

  async getMissionControlHealth() {
    return api.get('/api/v1/missions/health');
  },

  async getMissionGoals(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/goals?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionTasks(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/tasks?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionProgress(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/progress?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionBlockers(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/blockers?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionTimeline(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/timeline?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionDecisions(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/decisions?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMissionRisks(missionId, tenantId = 'default') {
    return api.get(`/api/v1/missions/${encodeURIComponent(missionId)}/risks?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async reassessMission(missionId, tenantId = 'default') {
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/reassess?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async verifyMission(missionId, telemetry = {}, tenantId = 'default') {
    return api.post(`/api/v1/missions/${encodeURIComponent(missionId)}/verify?tenant_id=${encodeURIComponent(tenantId)}`, telemetry);
  },

  // --- Task 67: Metacognitive Control & Autonomous Self-Audit Engine ---
  async createSelfAudit(payload) {
    return api.post('/api/v1/self-audit/', payload);
  },

  async runSelfAuditCycle(payload) {
    return api.post('/api/v1/self-audit/cycle', payload);
  },

  async listSelfAudits(tenantId = 'default') {
    return api.get(`/api/v1/self-audit/?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditOverview(tenantId = 'default') {
    return api.get(`/api/v1/self-audit/overview?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAudit(auditId, tenantId = 'default') {
    return api.get(`/api/v1/self-audit/${encodeURIComponent(auditId)}?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditFindings(auditId, tenantId = 'default') {
    return api.get(`/api/v1/self-audit/${encodeURIComponent(auditId)}/findings?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditEvidence(auditId, tenantId = 'default') {
    return api.get(`/api/v1/self-audit/${encodeURIComponent(auditId)}/evidence?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditHistory(tenantId = 'default') {
    return api.get(`/api/v1/self-audit/history?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditDrift(tenantId = 'default') {
    return api.get(`/api/v1/self-audit/drift?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditCalibration(tenantId = 'default') {
    return api.get(`/api/v1/self-audit/calibration?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditErrors(tenantId = 'default') {
    return api.get(`/api/v1/self-audit/errors?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async reassessSelfAudit(auditId, tenantId = 'default') {
    return api.post(`/api/v1/self-audit/${encodeURIComponent(auditId)}/reassess?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async listSelfAuditBeliefs(tenantId = 'default') {
    return api.get(`/api/v1/self-audit/beliefs?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async registerSelfAuditBelief(payload) {
    return api.post('/api/v1/self-audit/beliefs', payload);
  },

  async reviseSelfAuditBelief(beliefId, payload) {
    return api.post(`/api/v1/self-audit/beliefs/${encodeURIComponent(beliefId)}/revise`, payload);
  },

  async resolveSelfAuditFinding(findingId, evidence = '', tenantId = 'default') {
    return api.post(`/api/v1/self-audit/findings/${encodeURIComponent(findingId)}/resolve?evidence=${encodeURIComponent(evidence)}&tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getSelfAuditHealth() {
    return api.get('/api/v1/self-audit/health');
  },

  // --- Task 68: Autonomous Knowledge & Memory Consolidation Engine ---
  async captureMemory(payload, tenantId = 'default') {
    return api.post(`/api/v1/memory/capture?tenant_id=${encodeURIComponent(tenantId)}`, payload);
  },

  async searchConsolidatedMemories(params = {}, tenantId = 'default') {
    const queryParts = [`tenant_id=${encodeURIComponent(tenantId)}`];
    if (params.query || params.q) queryParts.push(`q=${encodeURIComponent(params.query || params.q)}`);
    if (params.top_k) queryParts.push(`top_k=${encodeURIComponent(params.top_k)}`);
    if (params.memory_type) queryParts.push(`memory_type=${encodeURIComponent(params.memory_type)}`);
    if (params.cognitive_type) queryParts.push(`cognitive_type=${encodeURIComponent(params.cognitive_type)}`);
    if (params.trust_level) queryParts.push(`trust_level=${encodeURIComponent(params.trust_level)}`);
    if (params.include_stale !== undefined) queryParts.push(`include_stale=${encodeURIComponent(params.include_stale)}`);
    return api.get(`/api/v1/memory/search?${queryParts.join('&')}`);
  },

  async getMemoryConflicts(tenantId = 'default') {
    return api.get(`/api/v1/memory/conflicts?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getStaleMemories(tenantId = 'default') {
    return api.get(`/api/v1/memory/stale?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getExpiringMemories(withinHours = 24, tenantId = 'default') {
    return api.get(`/api/v1/memory/expiring?within_hours=${encodeURIComponent(withinHours)}&tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMemoryHealth(tenantId = 'default') {
    return api.get(`/api/v1/memory/health?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async assembleMemoryContext(payload, tenantId = 'default') {
    return api.post(`/api/v1/memory/context?tenant_id=${encodeURIComponent(tenantId)}`, payload);
  },

  async triggerConsolidationSweep(tenantId = 'default') {
    return api.post(`/api/v1/memory/sweep?tenant_id=${encodeURIComponent(tenantId)}`, {});
  },

  async getMemoryProvenance(memoryId, tenantId = 'default') {
    return api.get(`/api/v1/memory/${encodeURIComponent(memoryId)}/provenance?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async getMemoryHistory(memoryId, tenantId = 'default') {
    return api.get(`/api/v1/memory/${encodeURIComponent(memoryId)}/history?tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async validateMemory(memoryId, verified = true, evidenceRef = '', tenantId = 'default') {
    return api.post(`/api/v1/memory/${encodeURIComponent(memoryId)}/validate?verified=${encodeURIComponent(verified)}&evidence_ref=${encodeURIComponent(evidenceRef)}&tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async promoteMemory(memoryId, reason = '', tenantId = 'default') {
    return api.post(`/api/v1/memory/${encodeURIComponent(memoryId)}/promote?reason=${encodeURIComponent(reason)}&tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async consolidateMemories(memoryId, relatedIds = [], tenantId = 'default') {
    const q = relatedIds.map(id => `related_ids=${encodeURIComponent(id)}`).join('&');
    const url = `/api/v1/memory/${encodeURIComponent(memoryId)}/consolidate?tenant_id=${encodeURIComponent(tenantId)}${q ? '&' + q : ''}`;
    return api.post(url, {});
  },

  async quarantineMemory(memoryId, reason = '', tenantId = 'default') {
    return api.post(`/api/v1/memory/${encodeURIComponent(memoryId)}/quarantine?reason=${encodeURIComponent(reason)}&tenant_id=${encodeURIComponent(tenantId)}`);
  },

  async forgetMemory(memoryId, reason = '', hardDelete = false, tenantId = 'default') {
    return api.post(`/api/v1/memory/${encodeURIComponent(memoryId)}/forget?reason=${encodeURIComponent(reason)}&hard_delete=${encodeURIComponent(hardDelete)}&tenant_id=${encodeURIComponent(tenantId)}`);
  },

  // --- Task 69: Universal Context & Adaptive Personalization Engine ---
  async buildUniversalContext(payload, tenantId = 'default') {
    return api.post('/api/v1/context/build', { tenant_id: tenantId, ...payload });
  },

  async previewUniversalContext(payload, tenantId = 'default') {
    return api.post('/api/v1/context/preview', { tenant_id: tenantId, ...payload });
  },

  async getContextQuality(tenantId = 'default') {
    return api.get(`/api/v1/context/quality`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getMissingContext(tenantId = 'default') {
    return api.get(`/api/v1/context/missing`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getContextConflicts(tenantId = 'default') {
    return api.get(`/api/v1/context/conflicts`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getUniversalContextHealth(tenantId = 'default') {
    return api.get(`/api/v1/context/health`, { headers: { 'x-tenant-id': tenantId } });
  },

  async listAdaptivePreferences(category = null, tenantId = 'default') {
    const qs = category ? `?category=${encodeURIComponent(category)}` : '';
    return api.get(`/api/v1/context/preferences${qs}`, { headers: { 'x-tenant-id': tenantId } });
  },

  async registerAdaptivePreference(payload, tenantId = 'default') {
    return api.post('/api/v1/context/preferences', { tenant_id: tenantId, ...payload }, { headers: { 'x-tenant-id': tenantId } });
  },

  async updateAdaptivePreference(preferenceId, payload, tenantId = 'default') {
    return api.patch(`/api/v1/context/preferences/${encodeURIComponent(preferenceId)}`, payload, { headers: { 'x-tenant-id': tenantId } });
  },

  async deleteAdaptivePreference(preferenceId, tenantId = 'default') {
    return api.delete(`/api/v1/context/preferences/${encodeURIComponent(preferenceId)}`, { headers: { 'x-tenant-id': tenantId } });
  },

  async listContextSnapshots(userId = null, limit = 50, tenantId = 'default') {
    let q = [`limit=${limit}`];
    if (userId) q.push(`user_id=${encodeURIComponent(userId)}`);
    return api.get(`/api/v1/context/snapshots?${q.join('&')}`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getContextSnapshot(snapshotId, tenantId = 'default') {
    return api.get(`/api/v1/context/snapshots/${encodeURIComponent(snapshotId)}`, { headers: { 'x-tenant-id': tenantId } });
  },

  async replayContextSnapshot(snapshotId, tenantId = 'default') {
    return api.get(`/api/v1/context/snapshots/${encodeURIComponent(snapshotId)}/replay`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getContextPackage(contextId, tenantId = 'default') {
    return api.get(`/api/v1/context/${encodeURIComponent(contextId)}`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getContextExplanation(contextId, tenantId = 'default') {
    return api.get(`/api/v1/context/${encodeURIComponent(contextId)}/explanation`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getContextSources(contextId, tenantId = 'default') {
    return api.get(`/api/v1/context/${encodeURIComponent(contextId)}/sources`, { headers: { 'x-tenant-id': tenantId } });
  },

  async refreshContextPackage(contextId, tenantId = 'default') {
    return api.post(`/api/v1/context/${encodeURIComponent(contextId)}/refresh`, {}, { headers: { 'x-tenant-id': tenantId } });
  },

  // --- Task 70: Autonomous Attention & Cognitive Resource Engine ---
  async evaluateAttentionCandidate(payload, tenantId = 'default') {
    return api.post('/api/v1/attention/evaluate', { tenant_id: tenantId, ...payload }, { headers: { 'x-tenant-id': tenantId } });
  },

  async getCurrentAttentionFocus(tenantId = 'default') {
    return api.get('/api/v1/attention/current', { headers: { 'x-tenant-id': tenantId } });
  },

  async getAttentionQueue(tenantId = 'default') {
    return api.get('/api/v1/attention/queue', { headers: { 'x-tenant-id': tenantId } });
  },

  async getAttentionSnapshot(tenantId = 'default') {
    return api.get('/api/v1/attention/snapshot', { headers: { 'x-tenant-id': tenantId } });
  },

  async getAttentionHealth(tenantId = 'default') {
    return api.get('/api/v1/attention/health', { headers: { 'x-tenant-id': tenantId } });
  },

  async getAttentionMetrics(tenantId = 'default') {
    return api.get('/api/v1/attention/metrics', { headers: { 'x-tenant-id': tenantId } });
  },

  async getAttentionCandidate(attentionId, tenantId = 'default') {
    return api.get(`/api/v1/attention/${encodeURIComponent(attentionId)}`, { headers: { 'x-tenant-id': tenantId } });
  },

  async focusAttentionCandidate(attentionId, tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/focus`, {}, { headers: { 'x-tenant-id': tenantId } });
  },

  async pauseAttentionCandidate(attentionId, reason = '', tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/pause`, { reason }, { headers: { 'x-tenant-id': tenantId } });
  },

  async resumeAttentionCandidate(attentionId, tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/resume`, {}, { headers: { 'x-tenant-id': tenantId } });
  },

  async deferAttentionCandidate(attentionId, reason = '', tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/defer`, { reason }, { headers: { 'x-tenant-id': tenantId } });
  },

  async delegateAttentionCandidate(attentionId, targetAgentId, reason = '', scope = 'full_investigation', tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/delegate`, { target_agent_id: targetAgentId, reason, scope }, { headers: { 'x-tenant-id': tenantId } });
  },

  async dismissAttentionCandidate(attentionId, reason = '', tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/dismiss`, { reason }, { headers: { 'x-tenant-id': tenantId } });
  },

  async escalateAttentionCandidate(attentionId, delta = 0.15, reason = '', tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/escalate`, { delta, reason }, { headers: { 'x-tenant-id': tenantId } });
  },

  async deescalateAttentionCandidate(attentionId, delta = 0.15, reason = '', tenantId = 'default') {
    return api.post(`/api/v1/attention/${encodeURIComponent(attentionId)}/deescalate`, { delta, reason }, { headers: { 'x-tenant-id': tenantId } });
  },

  async getAttentionExplanation(attentionId, tenantId = 'default') {
    return api.get(`/api/v1/attention/${encodeURIComponent(attentionId)}/explanation`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getAttentionHistory(attentionId, tenantId = 'default') {
    return api.get(`/api/v1/attention/${encodeURIComponent(attentionId)}/history`, { headers: { 'x-tenant-id': tenantId } });
  },

  // --- Task 71: Autonomous Reasoning & Deliberation Engine ---
  async startReasoning(payload, tenantId = 'default', workspaceId = 'default') {
    return api.post('/api/v1/reasoning/start', { tenant_id: tenantId, workspace_id: workspaceId, ...payload }, { headers: { 'x-tenant-id': tenantId, 'x-workspace-id': workspaceId } });
  },

  async listReasoningSessions(limit = 50, tenantId = 'default', workspaceId = 'default') {
    return api.get(`/api/v1/reasoning/sessions?limit=${limit}`, { headers: { 'x-tenant-id': tenantId, 'x-workspace-id': workspaceId } });
  },

  async getReasoningSession(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningHypotheses(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/hypotheses`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningEvidence(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/evidence`, { headers: { 'x-tenant-id': tenantId } });
  },

  async addReasoningEvidence(reasoningId, payload, tenantId = 'default') {
    return api.post(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/evidence`, payload, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningAssumptions(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/assumptions`, { headers: { 'x-tenant-id': tenantId } });
  },

  async invalidateReasoningAssumption(reasoningId, assumptionId, reason, tenantId = 'default') {
    return api.post(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/assumptions/${encodeURIComponent(assumptionId)}/invalidate`, { reason }, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningConclusion(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/conclusion`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningExplanation(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/explanation`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningTrace(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/trace`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningGraph(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/graph`, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningQuality(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/quality`, { headers: { 'x-tenant-id': tenantId } });
  },

  async replayReasoning(reasoningId, tenantId = 'default') {
    return api.get(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/replay`, { headers: { 'x-tenant-id': tenantId } });
  },

  async verifyReasoningConclusion(reasoningId, tenantId = 'default') {
    return api.post(`/api/v1/reasoning/${encodeURIComponent(reasoningId)}/verify`, {}, { headers: { 'x-tenant-id': tenantId } });
  },

  async getReasoningHealth() {
    return api.get('/api/v1/reasoning/health');
  },

  // --- Task 72: Autonomous Hypothesis, Experimentation & Scientific Discovery Engine ---
  async startDiscovery(payload, tenantId = 'default', workspaceId = 'default') {
    return api.post('/api/v1/discovery/start', payload, { headers: { 'x-tenant-id': tenantId, 'x-workspace-id': workspaceId } });
  },

  async getDiscovery(discoveryId) {
    return api.get(`/api/v1/discovery/${encodeURIComponent(discoveryId)}`);
  },

  async listDiscoveries(status = null, tenantId = 'default', workspaceId = 'default') {
    const q = status ? `?status_filter=${encodeURIComponent(status)}` : '';
    return api.get(`/api/v1/discovery${q}`, { headers: { 'x-tenant-id': tenantId, 'x-workspace-id': workspaceId } });
  },

  async addDiscoveryHypotheses(discoveryId, payload) {
    return api.post(`/api/v1/discovery/${encodeURIComponent(discoveryId)}/hypotheses`, payload);
  },

  async getDiscoveryHypotheses(discoveryId) {
    return api.get(`/api/v1/discovery/${encodeURIComponent(discoveryId)}/hypotheses`);
  },

  async concludeDiscovery(discoveryId) {
    return api.post(`/api/v1/discovery/${encodeURIComponent(discoveryId)}/conclude`, {});
  },

  async getDiscoveryAudit(discoveryId) {
    return api.get(`/api/v1/discovery/${encodeURIComponent(discoveryId)}/audit`);
  },

  async designExperiment(payload) {
    return api.post('/api/v1/experiments/design', payload);
  },

  async getExperiment(experimentId) {
    return api.get(`/api/v1/experiments/${encodeURIComponent(experimentId)}`);
  },

  async recordExperimentPrediction(experimentId, payload) {
    return api.post(`/api/v1/experiments/${encodeURIComponent(experimentId)}/prediction`, payload);
  },

  async approveExperiment(experimentId, approver) {
    return api.post(`/api/v1/experiments/${encodeURIComponent(experimentId)}/approve`, { approver });
  },

  async startExperiment(experimentId, payload = {}) {
    return api.post(`/api/v1/experiments/${encodeURIComponent(experimentId)}/start`, payload);
  },

  async recordExperimentObservation(experimentId, payload) {
    return api.post(`/api/v1/experiments/${encodeURIComponent(experimentId)}/observation`, payload);
  },

  async analyzeExperiment(experimentId, payload) {
    return api.post(`/api/v1/experiments/${encodeURIComponent(experimentId)}/analyze`, payload);
  },

  async rollbackExperiment(experimentId) {
    return api.post(`/api/v1/experiments/${encodeURIComponent(experimentId)}/rollback`, {});
  },

  async cleanupExperiment(experimentId) {
    return api.post(`/api/v1/experiments/${encodeURIComponent(experimentId)}/cleanup`, {});
  },

  async replicateExperiment(payload) {
    return api.post('/api/v1/experiments/replicate', payload);
  },

  async getExperimentExplanation(experimentId) {
    return api.get(`/api/v1/experiments/${encodeURIComponent(experimentId)}/explanation`);
  },

  async getExperimentQueue() {
    return api.get('/api/v1/experiments/queue');
  },

  async getDiscoveryHealth() {
    return api.get('/api/v1/experiments/health');
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

export const executiveMemoryApi = {
  queryContinuity: (payload) => Endpoints.queryExecutiveContinuity(payload),
  getState: () => Endpoints.getExecutiveState(),
  synthesizeState: (payload) => Endpoints.synthesizeExecutiveState(payload),
  listTimeline: (params) => Endpoints.listExecutiveTimeline(params),
  recordEvent: (payload) => Endpoints.recordExecutiveTimelineEvent(payload),
  reconstructAsOf: (params) => Endpoints.reconstructExecutiveAsOf(params),
  listOpenLoops: (params) => Endpoints.listExecutiveOpenLoops(params),
  createOpenLoop: (payload) => Endpoints.createExecutiveOpenLoop(payload),
  updateOpenLoopStatus: (id, payload) => Endpoints.updateExecutiveOpenLoopStatus(id, payload),
  closeOpenLoop: (id, payload) => Endpoints.closeExecutiveOpenLoop(id, payload),
  listBlockers: (params) => Endpoints.listExecutiveBlockers(params),
  createBlocker: (payload) => Endpoints.createExecutiveBlocker(payload),
  resolveBlocker: (id, payload) => Endpoints.resolveExecutiveBlocker(id, payload),
  listMilestones: (params) => Endpoints.listExecutiveMilestones(params),
  createMilestone: (payload) => Endpoints.createExecutiveMilestone(payload),
  achieveMilestone: (id, payload) => Endpoints.achieveExecutiveMilestone(id, payload),
  getBrief: (projectId) => Endpoints.getExecutiveBrief(projectId),
  generateBrief: (projectId, payload) => Endpoints.generateExecutiveBrief(projectId, payload),
  getNextActions: (params) => Endpoints.getExecutiveNextActions(params),
  createCheckpoint: (payload) => Endpoints.createExecutiveCheckpoint(payload),
  resumeCheckpoint: (id, payload) => Endpoints.resumeExecutiveCheckpoint(id, payload),
  reconcile: (payload) => Endpoints.reconcileExecutiveState(payload),
  getMetrics: () => Endpoints.getExecutiveMemoryMetrics(),
};

export const digitalTwinApi = {
  getTwin: (scope, scopeId) => Endpoints.getDigitalTwin(scope, scopeId),
  registerNode: (payload) => Endpoints.registerEnvironmentNode(payload),
  registerEdge: (payload) => Endpoints.registerEnvironmentEdge(payload),
  recordHealth: (payload) => Endpoints.recordEnvironmentHealth(payload),
  recordChange: (payload) => Endpoints.recordEnvironmentChange(payload),
  recordDrift: (payload) => Endpoints.recordEnvironmentDrift(payload),
  createSnapshot: (scope, scopeId) => Endpoints.createEnvironmentSnapshot(scope, scopeId),
  getStateAsOf: (asOf, scope, scopeId) => Endpoints.getEnvironmentStateAsOf(asOf, scope, scopeId),
  createIncident: (payload) => Endpoints.createEnvironmentIncident(payload),
  simulateWhatIf: (payload) => Endpoints.simulateEnvironmentWhatIf(payload),
  proposePlan: (payload) => Endpoints.proposeRemediationPlan(payload),
  autoHeal: (payload) => Endpoints.executeAutoHealing(payload),
  getSummary: (scope) => Endpoints.getEnvironmentSummary(scope),
  getContext: (query, scope) => Endpoints.getEnvironmentContext(query, scope),
  getDependents: (nodeId, scope) => Endpoints.getEnvironmentDependents(nodeId, scope),
  getDependencies: (nodeId, scope) => Endpoints.getEnvironmentDependencies(nodeId, scope),
  getUnhealthy: (scope) => Endpoints.getEnvironmentUnhealthy(scope),
  getProduction: () => Endpoints.getEnvironmentProduction(),
};

export const causalApi = {
  getGraph: (graphId) => Endpoints.getCausalGraph(graphId),
  addNode: (payload) => Endpoints.addCausalNode(payload),
  addEdge: (payload) => Endpoints.addCausalEdge(payload),
  analyzeRootCause: (payload) => Endpoints.analyzeCausalRootCause(payload),
  getAnalysis: (incidentId) => Endpoints.getCausalAnalysis(incidentId),
  getExplanation: (incidentId) => Endpoints.getCausalExplanation(incidentId),
  askQuestion: (payload) => Endpoints.askCausalQuestion(payload),
  proposeIntervention: (payload) => Endpoints.proposeCausalIntervention(payload),
  evaluateIntervention: (interventionId, payload) => Endpoints.evaluateCausalIntervention(interventionId, payload),
  evaluateCounterfactual: (payload) => Endpoints.evaluateCausalCounterfactual(payload),
  detectFallacies: (payload) => Endpoints.detectCausalFallacies(payload),
  getBlastRadius: (serviceName) => Endpoints.getCausalBlastRadius(serviceName),
};

export const simulationApi = {
  captureSnapshot: (payload) => Endpoints.captureSimulationSnapshot(payload),
  listSnapshots: () => Endpoints.listSimulationSnapshots(),
  getSnapshot: (snapshotId) => Endpoints.getSimulationSnapshot(snapshotId),
  createScenario: (payload) => Endpoints.createSimulationScenario(payload),
  listScenarios: (baselineSnapshotId) => Endpoints.listSimulationScenarios(baselineSnapshotId),
  getScenario: (scenarioId) => Endpoints.getSimulationScenario(scenarioId),
  runSimulation: (payload) => Endpoints.runSimulation(payload),
  listRuns: () => Endpoints.listSimulationRuns(),
  getRun: (simulationId) => Endpoints.getSimulationRun(simulationId),
  compareSimulations: (payload) => Endpoints.compareSimulations(payload),
  rankSimulations: (payload) => Endpoints.rankSimulations(payload),
  exploreCounterfactual: (payload) => Endpoints.exploreCounterfactual(payload),
  runMonteCarlo: (payload) => Endpoints.runMonteCarlo(payload),
  replay: (payload) => Endpoints.replaySimulation(payload),
  evaluateGate: (payload) => Endpoints.evaluateExecutionGate(payload),
  calibrate: (payload) => Endpoints.recordSimulationCalibration(payload),
  getCalibrationReport: (metricName) => Endpoints.getSimulationCalibrationReport(metricName),
};

export const decisionApi = {
  analyze: (payload) => Endpoints.analyzeDecision(payload),
  list: (limit) => Endpoints.listDecisions(limit),
  get: (decisionId) => Endpoints.getDecision(decisionId),
  select: (decisionId, payload) => Endpoints.selectDecisionOption(decisionId, payload),
  approve: (decisionId, payload) => Endpoints.approveDecision(decisionId, payload),
  revalidate: (decisionId) => Endpoints.revalidateDecision(decisionId),
  recordOutcome: (decisionId, payload) => Endpoints.recordDecisionOutcome(decisionId, payload),
  getOutcome: (decisionId) => Endpoints.getDecisionOutcome(decisionId),
  explain: (decisionId, query) => Endpoints.getDecisionExplanation(decisionId, query),
  reconstructAsOf: (decisionId) => Endpoints.getDecisionAsOf(decisionId),
  getAnalytics: () => Endpoints.getDecisionCalibrationAnalytics(),
};

export const planningApi = {
  create: (payload) => Endpoints.createPlan(payload),
  list: () => Endpoints.listPlans(),
  get: (planId) => Endpoints.getPlan(planId),
  validate: (planId, payload) => Endpoints.validatePlan(planId, payload),
  analyze: (planId) => Endpoints.analyzePlan(planId),
  start: (planId, payload) => Endpoints.startPlan(planId, payload),
  pause: (planId, payload) => Endpoints.pausePlan(planId, payload),
  resume: (planId, payload) => Endpoints.resumePlan(planId, payload),
  cancel: (planId, payload) => Endpoints.cancelPlan(planId, payload),
  replan: (planId, payload) => Endpoints.replan(planId, payload),
  getProgress: (planId) => Endpoints.getPlanProgress(planId),
  getTimeline: (planId) => Endpoints.getPlanTimeline(planId),
  getDependencies: (planId) => Endpoints.getPlanDependencies(planId),
  getRisks: (planId) => Endpoints.getPlanRisks(planId),
  getOutcomes: (planId) => Endpoints.getPlanOutcomes(planId),
  recordOutcome: (planId, payload) => Endpoints.recordPlanOutcome(planId, payload),
  getProposal: (planId) => Endpoints.getExecutionProposal(planId),
  getAudit: (planId) => Endpoints.getPlanAudit(planId),
};

export const orchestrationApi = {
  analyze: (payload) => Endpoints.analyzeOrchestration(payload),
  create: (payload) => Endpoints.createOrchestration(payload),
  listCapabilities: (env, status) => Endpoints.listCapabilities(env, status),
  listResources: (env, type) => Endpoints.listResources(env, type),
  reserveResource: (payload) => Endpoints.reserveResource(payload),
  releaseReservation: (id) => Endpoints.releaseReservation(id),
  list: (status, limit) => Endpoints.listOrchestrations(status, limit),
  get: (id) => Endpoints.getOrchestration(id),
  getAssignments: (id) => Endpoints.getOrchestrationAssignments(id),
  getTopology: (id) => Endpoints.getOrchestrationTopology(id),
  revalidate: (id, payload) => Endpoints.revalidateOrchestration(id, payload),
  failover: (id, payload) => Endpoints.failoverOrchestration(id, payload),
  getHealth: (id) => Endpoints.getOrchestrationHealth(id),
  explain: (taskId) => Endpoints.explainOrchestrationTask(taskId),
  getAudit: (id, limit) => Endpoints.getOrchestrationAudit(id, limit),
};

export const situationsApi = {
  ingest: (payload) => Endpoints.ingestSituationEvent(payload),
  list: (env, status) => Endpoints.listSituations(env, status),
  get: (id) => Endpoints.getSituation(id),
  getTimeline: (id) => Endpoints.getSituationTimeline(id),
  getImpact: (id) => Endpoints.getSituationImpact(id),
  getHypotheses: (id) => Endpoints.getSituationHypotheses(id),
  resolve: (id, payload) => Endpoints.resolveSituation(id, payload),
  escalate: (id, payload) => Endpoints.escalateSituation(id, payload),
  getAttentionFeed: () => Endpoints.getAttentionFeed(),
  getBaselines: (env) => Endpoints.listSignalBaselines(env),
  getAudit: (id, limit) => Endpoints.getSituationAudit(id, limit),
};

export const incidentsApi = {
  createFromSituation: (payload) => Endpoints.createIncidentFromSituation(payload),
  list: (env, status) => Endpoints.listIncidents(env, status),
  get: (id) => Endpoints.getIncident(id),
  triage: (id, payload) => Endpoints.triageIncident(id, payload),
  addEvidence: (id, payload) => Endpoints.addIncidentEvidence(id, payload),
  selectOption: (id, optId, payload) => Endpoints.selectIncidentOption(id, optId, payload),
  approveAction: (id, payload) => Endpoints.approveIncidentAction(id, payload),
  verifyCheckpoint: (id, payload) => Endpoints.verifyRecoveryCheckpoint(id, payload),
  resolve: (id, payload) => Endpoints.resolveIncident(id, payload),
  reopen: (id, payload) => Endpoints.reopenIncident(id, payload),
  getPostmortem: (id) => Endpoints.getIncidentPostmortem(id),
  getAudit: (id, limit) => Endpoints.getIncidentAudit(id, limit),
};

export const optimizationApi = {
  evaluate: (payload) => Endpoints.evaluateOptimization(payload),
  listRecommendations: () => Endpoints.listOptimizationRecommendations(),
  getRecommendation: (id) => Endpoints.getOptimizationRecommendation(id),
  approveRecommendation: (id, payload) => Endpoints.approveOptimizationRecommendation(id, payload),
  listExperiments: (status) => Endpoints.listOptimizationExperiments(status),
  createExperiment: (payload) => Endpoints.createOptimizationExperiment(payload),
  getExperiment: (id) => Endpoints.getOptimizationExperiment(id),
  approveExperiment: (id, approver) => Endpoints.approveOptimizationExperiment(id, approver),
  startExperiment: (id) => Endpoints.startOptimizationExperiment(id),
  deployCanary: (payload) => Endpoints.deployOptimizationCanary(payload),
  verifyCanary: (id, isVerified, advanceToFull) => Endpoints.verifyOptimizationCanary(id, isVerified, advanceToFull),
  rollbackCanary: (id, reason, actor) => Endpoints.rollbackOptimizationCanary(id, reason, actor),
  listChangeSets: () => Endpoints.listOptimizationChangeSets(),
  ingestMeasurement: (payload) => Endpoints.ingestOptimizationMeasurement(payload),
  getMetrics: () => Endpoints.getOptimizationMetrics(),
  listBaselines: () => Endpoints.listOptimizationBaselines(),
  listDrift: () => Endpoints.listOptimizationDrift(),
  listCalibration: () => Endpoints.listOptimizationCalibration(),
  getAudit: (csId, expId, limit) => Endpoints.getOptimizationAudit(csId, expId, limit),
  toggleKillSwitch: (payload) => Endpoints.toggleOptimizationKillSwitch(payload),
};

export const researchApi = {
  start: (payload) => Endpoints.startResearch(payload),
  list: (limit) => Endpoints.listResearchSessions(limit),
  get: (id) => Endpoints.getResearch(id),
  getSources: (id) => Endpoints.getResearchSources(id),
  getClaims: (id) => Endpoints.getResearchClaims(id),
  getEvidence: (id) => Endpoints.getResearchEvidence(id),
  getConflicts: (id) => Endpoints.getResearchConflicts(id),
  getGaps: (id) => Endpoints.getResearchGaps(id),
  getTimeline: (id) => Endpoints.getResearchTimeline(id),
  continue: (id, q) => Endpoints.continueResearch(id, q),
  verifyClaim: (id, payload) => Endpoints.verifyResearchClaim(id, payload),
  ingestDocument: (payload) => Endpoints.ingestResearchDocument(payload),
  getClaim: (id) => Endpoints.getResearchClaim(id),
  getSource: (id) => Endpoints.getResearchSource(id),
  retractSource: (id, reason) => Endpoints.retractResearchSource(id, reason),
  getDecisionPackage: (id) => Endpoints.getResearchDecisionPackage(id),
  getChanges: (limit) => Endpoints.getResearchKnowledgeChanges(limit),
  getAudit: (sessionId, sourceId, claimId, limit) => Endpoints.getResearchAudit(sessionId, sourceId, claimId, limit),
};

export const swarmApi = {
  create: (payload) => Endpoints.createSwarmSession(payload),
  createSession: (payload) => Endpoints.createSwarmSession(payload),
  list: (limit) => Endpoints.listSwarmSessions(limit),
  listSessions: (limit) => Endpoints.listSwarmSessions(limit),
  get: (id) => Endpoints.getSwarmSession(id),
  getSession: (id) => Endpoints.getSwarmSession(id),
  getAgents: (id) => Endpoints.getSwarmAgents(id),
  getTasks: (id) => Endpoints.getSwarmTasks(id),
  getResults: (id) => Endpoints.getSwarmResults(id),
  getReviews: (id) => Endpoints.getSwarmReviews(id),
  getDisagreements: (id) => Endpoints.getSwarmDisagreements(id),
  getMinorities: (id) => Endpoints.getSwarmMinorities(id),
  getMinorityReports: (id) => Endpoints.getSwarmMinorities(id),
  getTimeline: (id) => Endpoints.getSwarmTimeline(id),
  pause: (id) => Endpoints.pauseSwarm(id),
  resume: (id) => Endpoints.resumeSwarm(id),
  cancel: (id, payload) => Endpoints.cancelSwarm(id, payload),
  synthesize: (id) => Endpoints.synthesizeSwarm(id),
  verify: (id, notes) => Endpoints.verifySwarm(id, notes),
  getAudit: (id, limit) => Endpoints.getSwarmAudit(id, limit),
  getHealth: () => Endpoints.getSwarmHealth(),
};

export const foresightApi = {
  getHealth: () => Endpoints.getForesightHealth(),
  getOverview: () => Endpoints.getWorldModelOverview(),
  query: (payload) => Endpoints.queryWorldModel(payload),
  listEntities: (params) => Endpoints.listWorldEntities(params),
  getEntity: (id) => Endpoints.getWorldEntity(id),
  listRelationships: (params) => Endpoints.listWorldRelationships(params),
  getDiff: (ts) => Endpoints.getWorldDiff(ts),
  reassess: (payload) => Endpoints.reassessWorldModel(payload),
  createForecast: (payload) => Endpoints.createForecast(payload),
  listForecasts: (horizon) => Endpoints.listForecasts(horizon),
  getForecast: (id) => Endpoints.getForecast(id),
  getForecastEvidence: (id) => Endpoints.getForecastEvidence(id),
  getForecastAssumptions: (id) => Endpoints.getForecastAssumptions(id),
  getForecastScenarios: (id) => Endpoints.getForecastScenarios(id),
  getForecastOutcomes: (id) => Endpoints.getForecastOutcomes(id),
  createScenario: (payload) => Endpoints.createScenario(payload),
  listScenarios: (type) => Endpoints.listScenarios(type),
  listRisks: () => Endpoints.listStrategicRisks(),
  listOpportunities: () => Endpoints.listStrategicOpportunities(),
  listEarlyWarnings: () => Endpoints.listEarlyWarnings(),
  getAudit: (limit) => Endpoints.getForesightAudit(limit),
};

export const worldModelApi = foresightApi;

export const missionsApi = {
  createMission: (payload, isHumanApproved) => Endpoints.createMission(payload, isHumanApproved),
  listMissions: (tenantId) => Endpoints.listMissions(tenantId),
  getOverview: (tenantId) => Endpoints.getMissionOverview(tenantId),
  getMission: (id, tenantId) => Endpoints.getMission(id, tenantId),
  startMission: (id, tenantId) => Endpoints.startMission(id, tenantId),
  pauseMission: (id, reason, tenantId) => Endpoints.pauseMission(id, reason, tenantId),
  resumeMission: (id, tenantId) => Endpoints.resumeMission(id, tenantId),
  cancelMission: (id, reason, tenantId) => Endpoints.cancelMission(id, reason, tenantId),
  replanMission: (id, reason, tenantId) => Endpoints.replanMission(id, reason, tenantId),
  executeSupervisoryCycle: (id, payload, tenantId) => Endpoints.executeSupervisoryCycle(id, payload, tenantId),
  completeMission: (id, tenantId) => Endpoints.completeMission(id, tenantId),
  getAuditTrail: (id) => Endpoints.getMissionAuditTrail(id),
  verifyAuditChain: () => Endpoints.verifyMissionAuditChain(),
  getHealth: () => Endpoints.getMissionControlHealth(),
  getGoals: (id, tenantId) => Endpoints.getMissionGoals(id, tenantId),
  getTasks: (id, tenantId) => Endpoints.getMissionTasks(id, tenantId),
  getProgress: (id, tenantId) => Endpoints.getMissionProgress(id, tenantId),
  getBlockers: (id, tenantId) => Endpoints.getMissionBlockers(id, tenantId),
  getTimeline: (id, tenantId) => Endpoints.getMissionTimeline(id, tenantId),
  getDecisions: (id, tenantId) => Endpoints.getMissionDecisions(id, tenantId),
  getRisks: (id, tenantId) => Endpoints.getMissionRisks(id, tenantId),
  reassess: (id, tenantId) => Endpoints.reassessMission(id, tenantId),
  verify: (id, telemetry, tenantId) => Endpoints.verifyMission(id, telemetry, tenantId),
};

export const missionControlApi = missionsApi;

export const selfAuditApi = {
  createAudit: (payload) => Endpoints.createSelfAudit(payload),
  runCycle: (payload) => Endpoints.runSelfAuditCycle(payload),
  listAudits: (tenantId) => Endpoints.listSelfAudits(tenantId),
  getOverview: (tenantId) => Endpoints.getSelfAuditOverview(tenantId),
  getAudit: (id, tenantId) => Endpoints.getSelfAudit(id, tenantId),
  getFindings: (id, tenantId) => Endpoints.getSelfAuditFindings(id, tenantId),
  getEvidence: (id, tenantId) => Endpoints.getSelfAuditEvidence(id, tenantId),
  getHistory: (tenantId) => Endpoints.getSelfAuditHistory(tenantId),
  getDrift: (tenantId) => Endpoints.getSelfAuditDrift(tenantId),
  getCalibration: (tenantId) => Endpoints.getSelfAuditCalibration(tenantId),
  getErrors: (tenantId) => Endpoints.getSelfAuditErrors(tenantId),
  reassess: (id, tenantId) => Endpoints.reassessSelfAudit(id, tenantId),
  listBeliefs: (tenantId) => Endpoints.listSelfAuditBeliefs(tenantId),
  registerBelief: (payload) => Endpoints.registerSelfAuditBelief(payload),
  reviseBelief: (id, payload) => Endpoints.reviseSelfAuditBelief(id, payload),
  resolveFinding: (id, evidence, tenantId) => Endpoints.resolveSelfAuditFinding(id, evidence, tenantId),
  getHealth: () => Endpoints.getSelfAuditHealth(),
};

export const metacognitiveControlApi = selfAuditApi;

export const memoryConsolidationApi = {
  capture: (payload, tenantId) => Endpoints.captureMemory(payload, tenantId),
  search: (params, tenantId) => Endpoints.searchConsolidatedMemories(params, tenantId),
  getConflicts: (tenantId) => Endpoints.getMemoryConflicts(tenantId),
  getStale: (tenantId) => Endpoints.getStaleMemories(tenantId),
  getExpiring: (withinHours, tenantId) => Endpoints.getExpiringMemories(withinHours, tenantId),
  getHealth: (tenantId) => Endpoints.getMemoryHealth(tenantId),
  assembleContext: (payload, tenantId) => Endpoints.assembleMemoryContext(payload, tenantId),
  triggerSweep: (tenantId) => Endpoints.triggerConsolidationSweep(tenantId),
  getMemory: (id) => Endpoints.getMemory(id),
  getProvenance: (id, tenantId) => Endpoints.getMemoryProvenance(id, tenantId),
  getHistory: (id, tenantId) => Endpoints.getMemoryHistory(id, tenantId),
  validate: (id, verified, evidenceRef, tenantId) => Endpoints.validateMemory(id, verified, evidenceRef, tenantId),
  promote: (id, reason, tenantId) => Endpoints.promoteMemory(id, reason, tenantId),
  consolidate: (id, relatedIds, tenantId) => Endpoints.consolidateMemories(id, relatedIds, tenantId),
  quarantine: (id, reason, tenantId) => Endpoints.quarantineMemory(id, reason, tenantId),
  forget: (id, reason, hardDelete, tenantId) => Endpoints.forgetMemory(id, reason, hardDelete, tenantId),
};

export const universalContextApi = {
  buildContext: (payload, tenantId) => Endpoints.buildUniversalContext(payload, tenantId),
  previewContext: (payload, tenantId) => Endpoints.previewUniversalContext(payload, tenantId),
  getQuality: (tenantId) => Endpoints.getContextQuality(tenantId),
  getMissing: (tenantId) => Endpoints.getMissingContext(tenantId),
  getConflicts: (tenantId) => Endpoints.getContextConflicts(tenantId),
  getHealth: (tenantId) => Endpoints.getUniversalContextHealth(tenantId),
  listPreferences: (category, tenantId) => Endpoints.listAdaptivePreferences(category, tenantId),
  registerPreference: (payload, tenantId) => Endpoints.registerAdaptivePreference(payload, tenantId),
  updatePreference: (id, payload, tenantId) => Endpoints.updateAdaptivePreference(id, payload, tenantId),
  deletePreference: (id, tenantId) => Endpoints.deleteAdaptivePreference(id, tenantId),
  listSnapshots: (userId, limit, tenantId) => Endpoints.listContextSnapshots(userId, limit, tenantId),
  getSnapshot: (id, tenantId) => Endpoints.getContextSnapshot(id, tenantId),
  replaySnapshot: (id, tenantId) => Endpoints.replayContextSnapshot(id, tenantId),
  getContext: (id, tenantId) => Endpoints.getContextPackage(id, tenantId),
  getExplanation: (id, tenantId) => Endpoints.getContextExplanation(id, tenantId),
  getSources: (id, tenantId) => Endpoints.getContextSources(id, tenantId),
  refreshContext: (id, tenantId) => Endpoints.refreshContextPackage(id, tenantId),
};

export const contextCenterApi = universalContextApi;

export const attentionApi = {
  evaluate: (payload, tenantId) => Endpoints.evaluateAttentionCandidate(payload, tenantId),
  getCurrent: (tenantId) => Endpoints.getCurrentAttentionFocus(tenantId),
  getQueue: (tenantId) => Endpoints.getAttentionQueue(tenantId),
  getSnapshot: (tenantId) => Endpoints.getAttentionSnapshot(tenantId),
  getHealth: (tenantId) => Endpoints.getAttentionHealth(tenantId),
  getMetrics: (tenantId) => Endpoints.getAttentionMetrics(tenantId),
  getCandidate: (id, tenantId) => Endpoints.getAttentionCandidate(id, tenantId),
  focus: (id, tenantId) => Endpoints.focusAttentionCandidate(id, tenantId),
  pause: (id, reason, tenantId) => Endpoints.pauseAttentionCandidate(id, reason, tenantId),
  resume: (id, tenantId) => Endpoints.resumeAttentionCandidate(id, tenantId),
  defer: (id, reason, tenantId) => Endpoints.deferAttentionCandidate(id, reason, tenantId),
  delegate: (id, agentId, reason, scope, tenantId) => Endpoints.delegateAttentionCandidate(id, agentId, reason, scope, tenantId),
  dismiss: (id, reason, tenantId) => Endpoints.dismissAttentionCandidate(id, reason, tenantId),
  escalate: (id, delta, reason, tenantId) => Endpoints.escalateAttentionCandidate(id, delta, reason, tenantId),
  deescalate: (id, delta, reason, tenantId) => Endpoints.deescalateAttentionCandidate(id, delta, reason, tenantId),
  getExplanation: (id, tenantId) => Endpoints.getAttentionExplanation(id, tenantId),
  getHistory: (id, tenantId) => Endpoints.getAttentionHistory(id, tenantId),
};

export const cognitiveResourceApi = {
  getBudget: (tenantId) => Endpoints.getAttentionMetrics(tenantId),
  getHealth: (tenantId) => Endpoints.getAttentionHealth(tenantId),
};

export const attentionCenterApi = attentionApi;

export const reasoningApi = {
  start: (payload, tenantId, workspaceId) => Endpoints.startReasoning(payload, tenantId, workspaceId),
  listSessions: (limit, tenantId, workspaceId) => Endpoints.listReasoningSessions(limit, tenantId, workspaceId),
  getSession: (id, tenantId) => Endpoints.getReasoningSession(id, tenantId),
  getHypotheses: (id, tenantId) => Endpoints.getReasoningHypotheses(id, tenantId),
  getEvidence: (id, tenantId) => Endpoints.getReasoningEvidence(id, tenantId),
  addEvidence: (id, payload, tenantId) => Endpoints.addReasoningEvidence(id, payload, tenantId),
  getAssumptions: (id, tenantId) => Endpoints.getReasoningAssumptions(id, tenantId),
  invalidateAssumption: (id, asmId, reason, tenantId) => Endpoints.invalidateReasoningAssumption(id, asmId, reason, tenantId),
  getConclusion: (id, tenantId) => Endpoints.getReasoningConclusion(id, tenantId),
  getExplanation: (id, tenantId) => Endpoints.getReasoningExplanation(id, tenantId),
  getTrace: (id, tenantId) => Endpoints.getReasoningTrace(id, tenantId),
  getGraph: (id, tenantId) => Endpoints.getReasoningGraph(id, tenantId),
  getQuality: (id, tenantId) => Endpoints.getReasoningQuality(id, tenantId),
  replay: (id, tenantId) => Endpoints.replayReasoning(id, tenantId),
  verify: (id, tenantId) => Endpoints.verifyReasoningConclusion(id, tenantId),
  getHealth: () => Endpoints.getReasoningHealth(),
};

export const reasoningCenterApi = reasoningApi;

export const discoveryApi = {
  start: (payload, tenantId, workspaceId) => Endpoints.startDiscovery(payload, tenantId, workspaceId),
  get: (id) => Endpoints.getDiscovery(id),
  list: (status, tenantId, workspaceId) => Endpoints.listDiscoveries(status, tenantId, workspaceId),
  addHypotheses: (id, payload) => Endpoints.addDiscoveryHypotheses(id, payload),
  getHypotheses: (id) => Endpoints.getDiscoveryHypotheses(id),
  conclude: (id) => Endpoints.concludeDiscovery(id),
  getAudit: (id) => Endpoints.getDiscoveryAudit(id),
  designExperiment: (payload) => Endpoints.designExperiment(payload),
  getExperiment: (id) => Endpoints.getExperiment(id),
  recordPrediction: (id, payload) => Endpoints.recordExperimentPrediction(id, payload),
  approveExperiment: (id, approver) => Endpoints.approveExperiment(id, approver),
  startExperiment: (id, payload) => Endpoints.startExperiment(id, payload),
  recordObservation: (id, payload) => Endpoints.recordExperimentObservation(id, payload),
  analyzeExperiment: (id, payload) => Endpoints.analyzeExperiment(id, payload),
  rollbackExperiment: (id) => Endpoints.rollbackExperiment(id),
  cleanupExperiment: (id) => Endpoints.cleanupExperiment(id),
  replicate: (payload) => Endpoints.replicateExperiment(payload),
  getExplanation: (id) => Endpoints.getExperimentExplanation(id),
  getQueue: () => Endpoints.getExperimentQueue(),
  getHealth: () => Endpoints.getDiscoveryHealth(),
};

export const discoveryCenterApi = discoveryApi;

export const endpoints = Endpoints;





