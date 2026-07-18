//! `prometheus verify` — verify a package's signature and internal integrity.

use crate::pack::{read_signature, PackageSignature};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::Path;
use zip::ZipArchive;

/// The result of verifying a package.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VerificationStatus {
    /// HMAC and every file digest matched.
    Verified,
    /// HMAC over the file list did not match the developer key.
    BadSignature,
    /// HMAC matched but a file's content digest differed.
    BadIntegrity(String),
    /// The package is missing the signature descriptor.
    MissingDescriptor,
}

/// Errors surfaced while verifying (beyond a clean "failed" status).
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum VerifyError {
    #[error("package not found: {0}")]
    NotFound(String),
}

/// Verifies `archive_path` against `signing_key`.
///
/// This performs two checks:
/// 1. The descriptor's HMAC-SHA256 over the file list matches the key.
/// 2. Each file inside the archive hashes to the recorded digest.
pub fn run(archive_path: &Path, signing_key: &[u8]) -> Result<VerificationStatus, VerifyError> {
    if !archive_path.exists() {
        return Err(VerifyError::NotFound(archive_path.to_string_lossy().into_owned()));
    }

    let signature = match read_signature(archive_path) {
        Ok(s) => s,
        Err(_) => return Ok(VerificationStatus::MissingDescriptor),
    };

    if !signature.verify(signing_key) {
        return Ok(VerificationStatus::BadSignature);
    }

    match check_file_integrity(archive_path, &signature) {
        Ok(()) => Ok(VerificationStatus::Verified),
        Err(bad) => Ok(VerificationStatus::BadIntegrity(bad)),
    }
}

/// Recomputes each archived file's SHA-256 and compares it to the descriptor.
pub fn check_file_integrity(
    archive_path: &Path,
    signature: &PackageSignature,
) -> Result<(), String> {
    let file = std::fs::File::open(archive_path).map_err(|e| e.to_string())?;
    let mut archive = ZipArchive::new(file).map_err(|e| e.to_string())?;

    for (rel, expected_hex) in &signature.files {
        let mut entry = archive.by_name(rel).map_err(|_| rel.clone())?;
        let mut buf = Vec::new();
        entry.read_to_end(&mut buf).map_err(|e| e.to_string())?;
        let mut hasher = Sha256::new();
        hasher.update(&buf);
        let actual = hasher.finalize();
        let actual_hex: String = actual.iter().map(|b| format!("{b:02x}")).collect();
        if actual_hex != *expected_hex {
            return Err(rel.clone());
        }
    }
    Ok(())
}

/// Convenience helper that re-emits a human-readable status line.
pub fn status_message(status: &VerificationStatus) -> String {
    match status {
        VerificationStatus::Verified => "package verified".to_string(),
        VerificationStatus::BadSignature => "BAD SIGNATURE: HMAC did not match key".to_string(),
        VerificationStatus::BadIntegrity(f) => format!("INTEGRITY FAILURE in file: {f}"),
        VerificationStatus::MissingDescriptor => "package is missing its signature descriptor".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pack::PackOptions;
    use std::io::Write;
    use std::path::PathBuf;

    fn tmp() -> PathBuf {
        let mut d = std::env::temp_dir();
        d.push(format!("prom_verify_{}", uuid::Uuid::new_v4()));
        d
    }

    fn build_package() -> (PathBuf, PathBuf, Vec<u8>) {
        let root = tmp();
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(root.join("data.txt"), b"content").unwrap();
        let out = root.join("pkg.zip");
        let key = b"sign-key";
        let _ = crate::pack::run(&PackOptions {
            source: root.clone(),
            output: out.clone(),
            signing_key: key.to_vec(),
            key_id: vec![],
            stored: true,
        })
        .unwrap();
        (root, out, key.to_vec())
    }

    #[test]
    fn verify_good_package() {
        let (root, out, key) = build_package();
        let status = run(&out, &key).unwrap();
        assert_eq!(status, VerificationStatus::Verified);
        assert_eq!(status_message(&status), "package verified");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn verify_rejects_wrong_key() {
        let (root, out, _key) = build_package();
        let status = run(&out, b"wrong-key").unwrap();
        assert_eq!(status, VerificationStatus::BadSignature);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn verify_missing_package_errors() {
        let missing = std::env::temp_dir().join("does_not_exist_xyz.zip");
        assert!(matches!(run(&missing, b"k"), Err(VerifyError::NotFound(_))));
    }

    #[test]
    fn verify_missing_descriptor() {
        // A zip with no descriptor should report MissingDescriptor.
        let root = tmp();
        std::fs::create_dir_all(&root).unwrap();
        let out = root.join("bare.zip");
        let mut writer = zip::ZipWriter::new(std::fs::File::create(&out).unwrap());
        let opts = zip::write::SimpleFileOptions::default();
        writer.start_file("x.txt", opts).unwrap();
        writer.write_all(b"hi").unwrap();
        writer.finish().unwrap();
        let status = run(&out, b"k").unwrap();
        assert_eq!(status, VerificationStatus::MissingDescriptor);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn verify_detects_tampered_file() {
        let (root, out, key) = build_package();
        // Tamper the stored bytes of data.txt inside the zip and patch its CRC
        // so the archive still opens, while the recorded digest no longer
        // matches -> integrity failure (HMAC still passes).
        // `data.txt` is "content" (7 bytes); replace with an equal-length
        // payload so the zip layout stays intact while the digest changes.
        tamper_zip_entry(&out, "data.txt", b"TAMPERD");
        let status = run(&out, &key).unwrap();
        assert!(matches!(status, VerificationStatus::BadIntegrity(_)));
        let _ = std::fs::remove_dir_all(&root);
    }
}

/// Patches a stored (uncompressed) entry's raw bytes inside a zip and rewrites
/// its CRC-32 in both the local and central headers so the archive still
/// opens. Only valid for entries written with no compression.
#[cfg(test)]
fn tamper_zip_entry(zip_path: &Path, entry_name: &str, new_content: &[u8]) {
    use std::io::Write;
    let mut bytes = std::fs::read(zip_path).unwrap();

    // Locate the local file header for the entry by scanning signatures.
    let local_sig = 0x04034b50u32.to_le_bytes();
    let mut pos = 0usize;
    let name_bytes = entry_name.as_bytes();
    let mut found = None;
    while pos + 4 <= bytes.len() {
        if &bytes[pos..pos + 4] == local_sig {
            let name_len = u16::from_le_bytes([bytes[pos + 26], bytes[pos + 27]]) as usize;
            let extra_len = u16::from_le_bytes([bytes[pos + 28], bytes[pos + 29]]) as usize;
            let name_start = pos + 30;
            if &bytes[name_start..name_start + name_len] == name_bytes {
                let data_start = name_start + name_len + extra_len;
                found = Some((data_start, pos + 14 /* crc offset */));
                break;
            }
        }
        pos += 1;
    }
    let (data_start, crc_local_offset) = found.expect("entry not found in zip");

    // Replace the stored content in-place. Caller must supply equal-length
    // content so the zip layout (and all subsequent offsets) stay intact.
    let old_len = new_content.len();
    bytes.splice(data_start..data_start + old_len, new_content.iter().copied());

    // Recompute CRC-32 over the new content and patch the local header.
    let crc = crc32(new_content);
    let patched = crc.to_le_bytes();
    // After splice the offset shifts only if length changed; here equal, so
    // crc_local_offset is still valid.
    bytes[crc_local_offset..crc_local_offset + 4].copy_from_slice(&patched);

    // Patch the matching central directory CRC as well.
    let central_sig = 0x02014b50u32.to_le_bytes();
    let mut cpos = 0usize;
    while cpos + 4 <= bytes.len() {
        if &bytes[cpos..cpos + 4] == central_sig {
            let cname_len = u16::from_le_bytes([bytes[cpos + 28], bytes[cpos + 29]]) as usize;
            let cname_start = cpos + 46;
            if &bytes[cname_start..cname_start + cname_len] == name_bytes {
                let ccrc_offset = cpos + 16;
                bytes[ccrc_offset..ccrc_offset + 4].copy_from_slice(&patched);
                break;
            }
        }
        cpos += 1;
    }

    let mut f = std::fs::File::create(zip_path).unwrap();
    f.write_all(&bytes).unwrap();
}

#[cfg(test)]
fn crc32(data: &[u8]) -> u32 {
    let mut crc: u32 = 0xffff_ffff;
    for &b in data {
        crc ^= b as u32;
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (0xedb8_8320 & mask);
        }
    }
    !crc
}
