/**
 * Developer Panel component for Kairo.
 * Provides repository workspace inspection, Git status, diff viewer,
 * GitHub issues/PRs/checks, and proposed write action lifecycle.
 */

export class DeveloperPanel {
  constructor(options = {}) {
    this.selectedRepo = options.selectedRepo || null;
    this.branch = options.branch || "HEAD";
    this.status = options.status || {
      is_clean: true,
      staged_files: [],
      modified_files: [],
      untracked_files: [],
      deleted_files: [],
    };
    this.commits = options.commits || [];
    this.diff = options.diff || null;
    this.issues = options.issues || [];
    this.pullRequests = options.pullRequests || [];
    this.checks = options.checks || [];
    this.proposedChanges = options.proposedChanges || [];
    this.activeTab = options.activeTab || "status"; // "status" | "diff" | "issues" | "prs" | "checks" | "proposed"
  }

  setSelectedRepo(repoPath) {
    this.selectedRepo = repoPath;
  }

  setBranch(branchName) {
    this.branch = branchName;
  }

  updateStatus(statusObj) {
    this.status = { ...this.status, ...statusObj };
  }

  setCommits(commitList) {
    this.commits = Array.isArray(commitList) ? commitList : [];
  }

  setDiff(diffObj) {
    this.diff = diffObj;
  }

  setIssues(issueList) {
    this.issues = Array.isArray(issueList) ? issueList : [];
  }

  setPullRequests(prList) {
    this.pullRequests = Array.isArray(prList) ? prList : [];
  }

  setChecks(checkList) {
    this.checks = Array.isArray(checkList) ? checkList : [];
  }

  setActiveTab(tabName) {
    const validTabs = ["status", "diff", "issues", "prs", "checks", "proposed"];
    if (validTabs.includes(tabName)) {
      this.activeTab = tabName;
    }
  }

  /**
   * Stage a proposed change for future write workflows.
   * Enforces diff preview -> approval -> execution -> verification pipeline.
   */
  proposeChange({ description, diff, targetFile }) {
    const change = {
      id: `change_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      description: description || "Proposed code modification",
      diff: diff || "",
      targetFile: targetFile || "",
      lifecycle: "PROPOSED CHANGE", // "PROPOSED CHANGE" -> "DIFF PREVIEW" -> "APPROVAL" -> "EXECUTION" -> "VERIFICATION"
      status: "pending_approval",
      createdAt: new Date().toISOString(),
    };
    this.proposedChanges.push(change);
    return change;
  }

  approveChange(changeId) {
    const change = this.proposedChanges.find((c) => c.id === changeId);
    if (!change) throw new Error(`Proposed change '${changeId}' not found.`);
    change.lifecycle = "APPROVAL";
    change.status = "approved";
    return change;
  }

  render() {
    const cleanBadge = this.status.is_clean ? "clean" : "dirty";
    return {
      type: "DeveloperPanel",
      repository: this.selectedRepo || "No repository selected",
      branch: this.branch,
      statusBadge: cleanBadge,
      activeTab: this.activeTab,
      summary: {
        stagedCount: this.status.staged_files?.length || 0,
        modifiedCount: this.status.modified_files?.length || 0,
        untrackedCount: this.status.untracked_files?.length || 0,
        commitsCount: this.commits.length,
        issuesCount: this.issues.length,
        prsCount: this.pullRequests.length,
        checksCount: this.checks.length,
        proposedChangesCount: this.proposedChanges.length,
      },
      content: {
        status: this.status,
        diff: this.diff,
        commits: this.commits,
        issues: this.issues,
        pullRequests: this.pullRequests,
        checks: this.checks,
        proposedChanges: this.proposedChanges,
      },
    };
  }
}
