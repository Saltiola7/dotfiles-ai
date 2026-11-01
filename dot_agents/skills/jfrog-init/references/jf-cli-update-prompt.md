# Existing CLI below the required capability

The collection-wide minimum is JFrog CLI 2.106.0 for Agent Plugins Repositories;
selected commands can have separate version requirements. Compare the actual
selected executable and preserve its installer owner. A compatible newer version
qualifies without any update. An older version remains intact and is reported as
an unmet prerequisite, not automatically upgraded or reinstalled.

An explicitly authorized update follows that native owner's reviewed version,
compatibility, integrity and recovery procedure. Do not invoke global npm or the
upstream fallback installer, change PATH, migrate credentials or hide the required
minimum from the user. Existing task authority does not expand to another owner.
Official capability reference: [Agent Plugins Repositories](https://docs.jfrog.com/artifactory/docs/agent-plugins-repositories#configure-the-jfrog-cli).
