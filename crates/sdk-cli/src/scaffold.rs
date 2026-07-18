//! `prometheus new` — scaffolding for plugins, agents, and drivers.

use serde_json::json;
use std::fs;
use std::path::{Path, PathBuf};

/// The kind of project the CLI can scaffold.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScaffoldKind {
    Plugin,
    Agent,
    Driver,
}

impl ScaffoldKind {
    pub fn parse(s: &str) -> Option<ScaffoldKind> {
        match s.to_ascii_lowercase().as_str() {
            "plugin" => Some(ScaffoldKind::Plugin),
            "agent" => Some(ScaffoldKind::Agent),
            "driver" => Some(ScaffoldKind::Driver),
            _ => None,
        }
    }

    pub fn manifest_name(&self) -> &'static str {
        match self {
            ScaffoldKind::Plugin => "plugin.json",
            ScaffoldKind::Agent => "agent.json",
            ScaffoldKind::Driver => "driver.json",
        }
    }
}

/// Options controlling a scaffold invocation.
#[derive(Debug, Clone)]
pub struct ScaffoldOptions {
    pub name: String,
    pub author: String,
    pub version: String,
    pub output_dir: PathBuf,
}

impl Default for ScaffoldOptions {
    fn default() -> Self {
        Self {
            name: "my-extension".into(),
            author: "anonymous".into(),
            version: "0.1.0".into(),
            output_dir: PathBuf::from("."),
        }
    }
}

/// A file written during scaffolding, returned so callers can report it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScaffoldedFile {
    pub path: PathBuf,
    pub contents: String,
}

impl ScaffoldedFile {
    pub fn relative_to(&self, base: &Path) -> PathBuf {
        self.path.strip_prefix(base).unwrap_or(&self.path).to_path_buf()
    }
}

/// Errors specific to scaffolding.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum ScaffoldError {
    #[error("unknown scaffold kind: {0}")]
    UnknownKind(String),
    #[error("target directory already exists: {0}")]
    AlreadyExists(String),
    #[error("invalid name: {0}")]
    InvalidName(String),
    #[error("{0}")]
    Other(String),
}

fn validate_name(name: &str) -> Result<(), ScaffoldError> {
    if name.is_empty() || !name.chars().all(|c| c.is_alphanumeric() || c == '-' || c == '_') {
        return Err(ScaffoldError::InvalidName(name.to_string()));
    }
    Ok(())
}

fn plugin_manifest(name: &str, author: &str, version: &str) -> serde_json::Value {
    json!({
        "id": format!("plg-{}", name),
        "name": name,
        "version": version,
        "description": format!("A Prometheus plugin named {}", name),
        "author": author,
        "capabilities": ["analysis-tool"],
        "permissions": ["read_knowledge"],
        "entrypoint": "libplugin.so"
    })
}

fn driver_manifest(name: &str, author: &str, version: &str) -> serde_json::Value {
    json!({
        "id": format!("drv-{}", name),
        "name": name,
        "version": version,
        "description": format!("A Prometheus driver named {}", name),
        "author": author,
        "protocols": ["USB", "SERIAL"],
        "hal_traits": [{
            "name": "Probeable",
            "methods": [{ "name": "probe", "signature": "fn probe(&self, target: &str)" }],
            "safety_level": "safe"
        }],
        "entrypoint": "libdriver.so"
    })
}

fn agent_manifest(name: &str, author: &str, version: &str) -> serde_json::Value {
    json!({
        "id": format!("agent-{}", name),
        "name": name,
        "version": version,
        "description": format!("A Prometheus agent named {}", name),
        "author": author,
        "tools": ["run"],
        "model": "prometheus-titan",
        "entrypoint": "agent.py"
    })
}

fn rust_stub(kind: ScaffoldKind, name: &str) -> String {
    match kind {
        ScaffoldKind::Plugin => format!(
            "//! Generated {} plugin stub.\n\n\
             use sdk_core::plugin::{{BasePlugin, PluginManifest, PluginContext, Health, PluginError}};\n\n\
             pub struct {name}Plugin {{ manifest: PluginManifest }}\n\n\
             impl BasePlugin for {name}Plugin {{\n\
             \x20   fn manifest(&self) -> &PluginManifest {{ &self.manifest }}\n\
             \x20   fn initialize(&mut self, _ctx: &PluginContext) -> Result<(), PluginError> {{ Ok(()) }}\n\
             \x20   fn execute(&self, action: &str, payload: &serde_json::Value) -> Result<serde_json::Value, PluginError> {{ Ok(serde_json::json!({{ \"action\": action, \"payload\": payload }})) }}\n\
             \x20   fn shutdown(&mut self) -> Result<(), PluginError> {{ Ok(()) }}\n\
             \x20   fn health(&self) -> Health {{ Health::Healthy }}\n\
             }}\n",
            kind.manifest_name().trim_end_matches(".json")
        ),
        ScaffoldKind::Driver => format!(
            "//! Generated {} driver stub.\n\n\
             use sdk_core::driver::{{Hal, Protocol, ProbeResult}};\n\n\
             pub struct {name}Driver;\n\n\
             impl Hal for {name}Driver {{\n\
             \x20   fn probe(&self, protocol: Protocol, target: &str) -> ProbeResult {{\n\
             \x20\x20\x20\x20 ProbeResult {{ protocol, target: target.to_string(), handshake_success: false, error: Some(\"not implemented\".into()) }}\n\
             \x20   }}\n\
             }}\n",
            kind.manifest_name().trim_end_matches(".json")
        ),
        ScaffoldKind::Agent => format!(
            "# Generated {} agent stub.\n\n\
             def run(context):\n\
             \x20\x20\x20\x20 return {{\"status\": \"ok\", \"agent\": \"{name}\"}}\n",
            kind.manifest_name().trim_end_matches(".json")
        ),
    }
}

/// Builds the set of files to write for a scaffold without touching disk.
/// Returns the root directory name and the files (relative to that root).
pub fn plan(kind: ScaffoldKind, opts: &ScaffoldOptions) -> Result<(PathBuf, Vec<ScaffoldedFile>), ScaffoldError> {
    validate_name(&opts.name)?;
    let root = opts.output_dir.join(&opts.name);
    let manifest = match kind {
        ScaffoldKind::Plugin => plugin_manifest(&opts.name, &opts.author, &opts.version),
        ScaffoldKind::Driver => driver_manifest(&opts.name, &opts.author, &opts.version),
        ScaffoldKind::Agent => agent_manifest(&opts.name, &opts.author, &opts.version),
    };
    let stub = match kind {
        ScaffoldKind::Plugin => rust_stub(ScaffoldKind::Plugin, &capitalize(&opts.name)),
        ScaffoldKind::Driver => rust_stub(ScaffoldKind::Driver, &capitalize(&opts.name)),
        ScaffoldKind::Agent => rust_stub(ScaffoldKind::Agent, &opts.name),
    };

    let mut files = vec![
        ScaffoldedFile {
            path: root.join(kind.manifest_name()),
            contents: serde_json::to_string_pretty(&manifest).expect("manifest serializes"),
        },
        ScaffoldedFile {
            path: root.join("README.md"),
            contents: format!("# {}\n\n{} generated by `prometheus new`.\n", opts.name, kind.manifest_name()),
        },
    ];

    let src_entry = match kind {
        ScaffoldKind::Plugin => "src/lib.rs",
        ScaffoldKind::Driver => "src/lib.rs",
        ScaffoldKind::Agent => "agent.py",
    };
    files.push(ScaffoldedFile {
        path: root.join(src_entry),
        contents: stub,
    });

    if kind == ScaffoldKind::Plugin || kind == ScaffoldKind::Driver {
        files.push(ScaffoldedFile {
            path: root.join("Cargo.toml"),
            contents: cargo_toml(kind, &opts.name, &opts.version),
        });
    }
    Ok((root, files))
}

fn cargo_toml(_kind: ScaffoldKind, name: &str, version: &str) -> String {
    let crate_name = name.replace('-', "_");
    format!(
        "[package]\n\
         name = \"{crate_name}\"\n\
         version = \"{version}\"\n\
         edition = \"2021\"\n\n\
         [dependencies]\n\
         sdk-core = {{ path = \"../sdk-core\" }}\n\
         serde = {{ version = \"1\", features = [\"derive\"] }}\n\
         serde_json = \"1\"\n\n\
         [lib]\n\
         name = \"{crate_name}\"\n"
    )
}

fn capitalize(s: &str) -> String {
    let mut c = s.chars();
    match c.next() {
        Some(first) => first.to_uppercase().collect::<String>() + c.as_str(),
        None => String::new(),
    }
}

/// Scaffolds the project to disk, returning the files written.
pub fn run(kind: ScaffoldKind, opts: &ScaffoldOptions) -> Result<Vec<ScaffoldedFile>, ScaffoldError> {
    let (root, files) = plan(kind, opts)?;
    if root.exists() {
        return Err(ScaffoldError::AlreadyExists(root.to_string_lossy().into_owned()));
    }
    fs::create_dir_all(&root).map_err(|e| ScaffoldError::Other(e.to_string()))?;
    for f in &files {
        if let Some(parent) = f.path.parent() {
            fs::create_dir_all(parent).map_err(|e| ScaffoldError::Other(e.to_string()))?;
        }
        fs::write(&f.path, &f.contents).map_err(|e| ScaffoldError::Other(e.to_string()))?;
        tracing::info!(path = %f.path.display(), "scaffolded file");
    }
    Ok(files)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp() -> PathBuf {
        let mut dir = std::env::temp_dir();
        dir.push(format!("prom_scaffold_{}", uuid::Uuid::new_v4()));
        dir
    }

    #[test]
    fn kind_parse() {
        assert_eq!(ScaffoldKind::parse("plugin"), Some(ScaffoldKind::Plugin));
        assert_eq!(ScaffoldKind::parse("DRIVER"), Some(ScaffoldKind::Driver));
        assert_eq!(ScaffoldKind::parse("wat"), None);
    }

    #[test]
    fn plan_plugin_has_expected_files() {
        let opts = ScaffoldOptions {
            name: "demo".into(),
            author: "me".into(),
            version: "1.2.3".into(),
            output_dir: PathBuf::from("/tmp/x"),
        };
        let (root, files) = plan(ScaffoldKind::Plugin, &opts).unwrap();
        assert_eq!(root, PathBuf::from("/tmp/x/demo"));
        let names: Vec<String> = files.iter().map(|f| f.relative_to(&root).to_string_lossy().into_owned()).collect();
        assert!(names.contains(&"plugin.json".to_string()));
        assert!(names.contains(&"src/lib.rs".to_string()));
        assert!(names.contains(&"Cargo.toml".to_string()));
        assert!(names.contains(&"README.md".to_string()));
    }

    #[test]
    fn plan_rejects_bad_name() {
        let opts = ScaffoldOptions {
            name: "bad name!".into(),
            output_dir: PathBuf::from("/tmp/x"),
            ..Default::default()
        };
        assert!(matches!(plan(ScaffoldKind::Plugin, &opts), Err(ScaffoldError::InvalidName(_))));
    }

    #[test]
    fn run_writes_to_disk() {
        let base = tmp();
        let opts = ScaffoldOptions {
            name: "agent1".into(),
            author: "tester".into(),
            version: "0.1.0".into(),
            output_dir: base.clone(),
        };
        let files = run(ScaffoldKind::Agent, &opts).unwrap();
        let root = base.join("agent1");
        assert!(root.join("agent.json").exists());
        assert!(root.join("agent.py").exists());
        let _ = fs::remove_dir_all(&base);
        assert!(!files.is_empty());
    }

    #[test]
    fn run_fails_if_exists() {
        let base = tmp();
        fs::create_dir_all(base.join("dup")).unwrap();
        let opts = ScaffoldOptions {
            name: "dup".into(),
            output_dir: base.clone(),
            ..Default::default()
        };
        assert!(matches!(run(ScaffoldKind::Plugin, &opts), Err(ScaffoldError::AlreadyExists(_))));
        let _ = fs::remove_dir_all(&base);
    }
}
