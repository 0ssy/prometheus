//! Context engine — reserved for Stage 4. Stubbed in Milestone 1.

/// A context packet assembled from workspace/project/knowledge/memory/hardware/
/// agents/terminal sources. In M1 it is always empty; later stages populate it
/// from the existing Prometheus REST endpoints (`/knowledge`, `/memory`,
/// `/devices`, `/agents`) and the terminal history.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct Context {
    #[serde(default)]
    pub workspace: Vec<String>,
    #[serde(default)]
    pub project: Vec<String>,
    #[serde(default)]
    pub files: Vec<String>,
    #[serde(default)]
    pub knowledge: Vec<String>,
    #[serde(default)]
    pub memory: Vec<String>,
    #[serde(default)]
    pub hardware: Vec<String>,
    #[serde(default)]
    pub agents: Vec<String>,
    #[serde(default)]
    pub terminal: Vec<String>,
}

impl Context {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn is_empty(&self) -> bool {
        self.workspace.is_empty()
            && self.project.is_empty()
            && self.files.is_empty()
            && self.knowledge.is_empty()
            && self.memory.is_empty()
            && self.hardware.is_empty()
            && self.agents.is_empty()
            && self.terminal.is_empty()
    }
}

/// Assembles a [`Context`] for the next model turn.
///
/// Stage 4 contract: pull from `/knowledge`, `/memory`, `/devices`, `/agents`
/// and terminal history via the REST API, then rank/trim to the model window.
/// In M1 it returns [`Context::empty`].
#[derive(Clone, Default)]
pub struct ContextEngine;

impl ContextEngine {
    pub fn new() -> Self {
        Self
    }

    /// Build a context packet. Always empty in M1.
    pub async fn assemble(&self) -> Context {
        Context::empty()
    }
}
