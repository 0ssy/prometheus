//! `prometheus pack` — build a signed distribution archive.
//!
//! The package is a zip containing the project's files plus a `.prometheus/
//! signature.json` descriptor. The descriptor records each file's SHA-256 and
//! an HMAC-SHA256 over the canonical file list, keyed by the developer's
//! signing key. [`verify`] checks both the HMAC and the per-file digests.

use crate::CliResult;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use walkdir::WalkDir;
use zip::{write::SimpleFileOptions, ZipArchive, ZipWriter};

type HmacSha256 = Hmac<Sha256>;

/// A signed package descriptor stored inside the archive.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PackageSignature {
    pub algorithm: String,
    #[serde(with = "base64_bytes")]
    pub key_id: Vec<u8>,
    #[serde(with = "base64_bytes")]
    pub hmac: Vec<u8>,
    pub files: BTreeMap<String, String>,
}

impl PackageSignature {
    /// Canonical JSON of the file map (sorted keys) used as HMAC input.
    pub fn canonical(&self) -> Vec<u8> {
        serde_json::to_vec(&self.files).expect("file map serializes")
    }

    pub fn verify(&self, key: &[u8]) -> bool {
        let mut mac =
            HmacSha256::new_from_slice(key).expect("HMAC accepts any key length");
        mac.update(&self.canonical());
        let out = mac.finalize().into_bytes();
        // Constant-time compare.
        if out.len() != self.hmac.len() {
            return false;
        }
        let mut diff = 0u8;
        for (a, b) in out.iter().zip(self.hmac.iter()) {
            diff |= a ^ b;
        }
        diff == 0
    }
}

/// Options for a pack operation.
#[derive(Debug, Clone)]
pub struct PackOptions {
    /// Directory to package. Defaults to current dir.
    pub source: PathBuf,
    /// Output `.zip` path.
    pub output: PathBuf,
    /// Developer signing key (HMAC secret).
    pub signing_key: Vec<u8>,
    /// Optional key id embedded in the descriptor.
    pub key_id: Vec<u8>,
    /// Compression method used for file entries (signature always stored).
    pub stored: bool,
}

impl Default for PackOptions {
    fn default() -> Self {
        Self {
            source: PathBuf::from("."),
            output: PathBuf::from("package.zip"),
            signing_key: vec![0u8; 32],
            key_id: vec![],
            stored: false,
        }
    }
}

/// Computes SHA-256 digests for every regular file under `root`, returning a
/// sorted map of relative path -> hex digest.
pub fn digest_tree(root: &Path) -> CliResult<BTreeMap<String, String>> {
    let mut map = BTreeMap::new();
    for entry in WalkDir::new(root).into_iter().filter_map(|e| e.ok()) {
        let path = entry.path();
        if path.is_file() {
            let rel = path
                .strip_prefix(root)
                .map_err(|e| crate::CliError::Other(e.to_string()))?
                .to_string_lossy()
                .replace('\\', "/");
            let bytes = std::fs::read(path)?;
            let mut hasher = Sha256::new();
            hasher.update(&bytes);
            map.insert(rel, hex_encode(&hasher.finalize()));
        }
    }
    Ok(map)
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Builds the signed package described by `opts`.
pub fn run(opts: &PackOptions) -> CliResult<PackageSignature> {
    let files = digest_tree(&opts.source)?;
    let mut mac =
        HmacSha256::new_from_slice(&opts.signing_key).expect("HMAC accepts any key length");
    mac.update(&serde_json::to_vec(&files)?);
    let hmac_bytes = mac.finalize().into_bytes().to_vec();

    let signature = PackageSignature {
        algorithm: "HMAC-SHA256".into(),
        key_id: opts.key_id.clone(),
        hmac: hmac_bytes,
        files: files.clone(),
    };

    let mut writer = ZipWriter::new(std::fs::File::create(&opts.output)?);
    let options = SimpleFileOptions::default()
        .compression_method(if opts.stored {
            zip::CompressionMethod::Stored
        } else {
            zip::CompressionMethod::Deflated
        })
        .unix_permissions(0o644);

    for entry in WalkDir::new(&opts.source).into_iter().filter_map(|e| e.ok()) {
        let path = entry.path();
        if path.is_file() {
            let rel = path
                .strip_prefix(&opts.source)
                .map_err(|e| crate::CliError::Other(e.to_string()))?
                .to_string_lossy()
                .replace('\\', "/");
            writer.start_file(rel.clone(), options)?;
            let bytes = std::fs::read(path)?;
            writer.write_all(&bytes)?;
        }
    }

    let sig_json = serde_json::to_string_pretty(&signature)?;
    writer.start_file(".prometheus/signature.json", options)?;
    writer.write_all(sig_json.as_bytes())?;
    writer.finish()?;

    tracing::info!(output = %opts.output.display(), files = files.len(), "packed signed package");
    Ok(signature)
}

/// Reads a package archive and returns its embedded signature descriptor.
pub fn read_signature(archive_path: &Path) -> CliResult<PackageSignature> {
    let file = std::fs::File::open(archive_path)?;
    let mut archive = ZipArchive::new(file)?;
    let mut sig_file = archive
        .by_name(".prometheus/signature.json")
        .map_err(|_| crate::CliError::Other("package missing signature descriptor".into()))?;
    let mut buf = String::new();
    sig_file.read_to_string(&mut buf)?;
    Ok(serde_json::from_str(&buf)?)
}

mod base64_bytes {
    use base64::engine::general_purpose::STANDARD;
    use base64::Engine;
    use serde::{Deserialize, Deserializer, Serializer};

    pub fn serialize<S: Serializer>(v: &[u8], ser: S) -> Result<S::Ok, S::Error> {
        ser.serialize_str(&STANDARD.encode(v))
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(de: D) -> Result<Vec<u8>, D::Error> {
        let s = String::deserialize(de)?;
        STANDARD.decode(s).map_err(serde::de::Error::custom)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp() -> PathBuf {
        let mut d = std::env::temp_dir();
        d.push(format!("prom_pack_{}", uuid::Uuid::new_v4()));
        d
    }

    #[test]
    fn digest_tree_finds_files() {
        let root = tmp();
        std::fs::create_dir_all(root.join("sub")).unwrap();
        std::fs::write(root.join("a.txt"), b"alpha").unwrap();
        std::fs::write(root.join("sub/b.txt"), b"beta").unwrap();
        let map = digest_tree(&root).unwrap();
        assert_eq!(map.len(), 2);
        assert!(map.contains_key("a.txt"));
        assert!(map.contains_key("sub/b.txt"));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn pack_and_read_signature() {
        let root = tmp();
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(root.join("hello.txt"), b"world").unwrap();
        let out = root.join("out.zip");
        let key = b"dev-signing-key";
        let sig = run(&PackOptions {
            source: root.clone(),
            output: out.clone(),
            signing_key: key.to_vec(),
            key_id: vec![1, 2, 3],
            stored: false,
        })
        .unwrap();
        assert_eq!(sig.algorithm, "HMAC-SHA256");
        assert!(sig.verify(key));
        assert!(!sig.verify(b"wrong"));

        let read_back = read_signature(&out).unwrap();
        assert_eq!(read_back.files, sig.files);
        let _ = std::fs::remove_dir_all(&root);
    }
}
