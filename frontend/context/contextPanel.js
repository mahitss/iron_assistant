/**
 * ContextPanel — Frontend state controller and view logic for Kairo Personal Context Engine.
 * Manages active projects, contextual item inspection with provenance, and personalization preferences.
 */

export class ContextPanel {
  constructor(options = {}) {
    this.userId = options.userId || 'default_user';
    this.activeProject = options.activeProject || null;
    this.projects = options.projects || [];
    this.contextItems = options.contextItems || [];
    this.settings = {
      context_enabled: true,
      memory_enabled: true,
      project_context_enabled: true,
      proactive_context_enabled: true,
      ...options.settings,
    };
  }

  setActiveProject(project) {
    this.activeProject = project;
    if (project && !this.projects.some((p) => p.id === project.id)) {
      this.projects.push(project);
    }
    return this.activeProject;
  }

  setContextItems(items = []) {
    this.contextItems = items.map((item) => ({
      source_type: item.source_type,
      source_id: item.source_id,
      title: item.title,
      content: item.content,
      relevance_score: item.relevance_score || 0.0,
      confidence: item.confidence !== undefined ? item.confidence : 1.0,
      timestamp: item.timestamp || new Date().toISOString(),
      reason: item.reason || 'Relevant to current task',
    }));
    return this.contextItems;
  }

  toggleSetting(settingKey) {
    if (Object.prototype.hasOwnProperty.call(this.settings, settingKey)) {
      this.settings[settingKey] = !this.settings[settingKey];
      return this.settings[settingKey];
    }
    throw new Error(`Unknown context setting: ${settingKey}`);
  }

  getGroupedContext() {
    const grouped = {
      project: [],
      memory: [],
      workflow: [],
      proactive: [],
      session: [],
      developer: [],
    };

    for (const item of this.contextItems) {
      if (item.source_type.includes('PROJECT')) grouped.project.push(item);
      else if (item.source_type.includes('MEMORY')) grouped.memory.push(item);
      else if (item.source_type.includes('WORKFLOW')) grouped.workflow.push(item);
      else if (item.source_type.includes('PROACTIVE')) grouped.proactive.push(item);
      else if (item.source_type.includes('SESSION')) grouped.session.push(item);
      else if (item.source_type.includes('DEVELOPER')) grouped.developer.push(item);
    }

    return grouped;
  }

  inspectProvenance(sourceId) {
    const item = this.contextItems.find((i) => i.source_id === sourceId);
    if (!item) {
      return null;
    }
    return {
      title: item.title,
      reason: item.reason,
      source_type: item.source_type,
      timestamp: item.timestamp,
    };
  }
}
