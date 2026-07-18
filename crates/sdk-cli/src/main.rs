//! `prometheus` — SDK developer CLI (Rust implementation).
//!
//! Usage:
//!   prometheus new <plugin|agent|driver> [--name NAME] [--author AUTHOR] [--output DIR]
//!   prometheus pack --source DIR --output FILE --key KEY
//!   prometheus verify --package FILE --key KEY

use clap::{Parser, Subcommand};
use sdk_cli::pack::PackOptions;
use sdk_cli::scaffold::{self, ScaffoldKind, ScaffoldOptions};
use sdk_cli::verify::{self, VerificationStatus};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "prometheus", version, about = "Prometheus Phase 9 SDK developer CLI")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Scaffold a new plugin, agent, or driver project.
    New {
        /// What to scaffold: plugin | agent | driver
        kind: String,
        /// Project name (alphanumeric, dash, underscore).
        #[arg(long, default_value = "my-extension")]
        name: String,
        /// Author name embedded in the manifest.
        #[arg(long, default_value = "anonymous")]
        author: String,
        /// Initial version.
        #[arg(long, default_value = "0.1.0")]
        version: String,
        /// Output directory.
        #[arg(long, default_value = ".")]
        output: PathBuf,
    },
    /// Pack a project directory into a signed distribution archive.
    Pack {
        /// Source directory to package.
        #[arg(long, default_value = ".")]
        source: PathBuf,
        /// Output `.zip` path.
        #[arg(long, default_value = "package.zip")]
        output: PathBuf,
        /// Signing key (HMAC secret). Hex or raw string.
        #[arg(long)]
        key: String,
    },
    /// Verify a signed distribution archive.
    Verify {
        /// Package `.zip` to verify.
        #[arg(long)]
        package: PathBuf,
        /// Signing key (HMAC secret). Hex or raw string.
        #[arg(long)]
        key: String,
    },
}

fn decode_key(s: &str) -> Vec<u8> {
    if let Ok(hex) = hex::decode(s) {
        if !s.is_empty() && s.len() % 2 == 0 && hex.len() > 0 {
            return hex;
        }
    }
    s.as_bytes().to_vec()
}

fn main() -> sdk_cli::CliResult<()> {
    tracing_subscriber::fmt::init();
    let cli = Cli::parse();

    match cli.command {
        Command::New {
            kind,
            name,
            author,
            version,
            output,
        } => {
            let k = ScaffoldKind::parse(&kind).unwrap_or_else(|| {
                eprintln!("unknown scaffold kind: {kind}");
                std::process::exit(2);
            });
            let opts = ScaffoldOptions {
                name,
                author,
                version,
                output_dir: output,
            };
            let files = scaffold::run(k, &opts).map_err(|e| sdk_cli::CliError::Other(e.to_string()))?;
            println!("Scaffolded {} project:", kind);
            for f in &files {
                println!("  {}", f.path.display());
            }
        }
        Command::Pack {
            source,
            output,
            key,
        } => {
            let opts = PackOptions {
                source,
                output,
                signing_key: decode_key(&key),
                key_id: vec![],
                stored: false,
            };
            let sig = sdk_cli::pack::run(&opts)?;
            println!(
                "Packed {} file(s) into {} (algorithm: {})",
                sig.files.len(),
                opts.output.display(),
                sig.algorithm
            );
        }
        Command::Verify { package, key } => {
            let status = verify::run(&package, &decode_key(&key))
                .map_err(|e| sdk_cli::CliError::Other(e.to_string()))?;
            println!("{}", verify::status_message(&status));
            if status != VerificationStatus::Verified {
                std::process::exit(1);
            }
        }
    }
    Ok(())
}
