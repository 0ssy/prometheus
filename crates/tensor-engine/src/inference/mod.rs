//! P6 Inference Engine — KV-cache, continuous batching, and attention kernels.
//!
//! Provides efficient transformer inference primitives:
//! - KV-cache management for autoregressive generation
//! - Continuous batching for multiple concurrent sequences
//! - FlashAttention-style scaled dot-product attention

use std::collections::VecDeque;

/// Maximum sequence length for KV-cache pre-allocation.
pub const MAX_SEQ_LEN: usize = 8192;
/// Default number of concurrent sequences in a batch.
pub const DEFAULT_BATCH_SIZE: usize = 32;
/// Default hidden dimension for attention.
pub const DEFAULT_HIDDEN_DIM: usize = 4096;
/// Default number of attention heads.
pub const DEFAULT_NUM_HEADS: usize = 32;
/// Default head dimension.
pub const DEFAULT_HEAD_DIM: usize = 128;

/// KV-cache entry for a single sequence.
#[derive(Debug, Clone)]
pub struct KVCacheEntry {
    pub sequence_id: u64,
    pub tokens: Vec<u32>,
    pub key_cache: Vec<f32>,
    pub value_cache: Vec<f32>,
    pub current_length: usize,
    pub is_finished: bool,
}

impl KVCacheEntry {
    /// Create a new empty KV-cache entry.
    pub fn new(sequence_id: u64, num_heads: usize, head_dim: usize, max_len: usize) -> Self {
        Self {
            sequence_id,
            tokens: Vec::with_capacity(max_len),
            key_cache: vec![0.0f32; num_heads * max_len * head_dim],
            value_cache: vec![0.0f32; num_heads * max_len * head_dim],
            current_length: 0,
            is_finished: false,
        }
    }

    /// Append a token to the sequence and update cache length.
    pub fn append_token(&mut self, token: u32) {
        self.tokens.push(token);
        self.current_length += 1;
    }

    /// Get the current sequence length.
    pub fn len(&self) -> usize {
        self.current_length
    }

    /// Check if the cache is empty.
    pub fn is_empty(&self) -> bool {
        self.current_length == 0
    }
}

/// KV-cache manager for multiple concurrent sequences.
#[derive(Debug, Default)]
pub struct KVCacheManager {
    entries: Vec<KVCacheEntry>,
    free_ids: VecDeque<usize>,
    num_heads: usize,
    head_dim: usize,
    max_len: usize,
}

impl KVCacheManager {
    /// Create a new KV-cache manager.
    pub fn new(num_heads: usize, head_dim: usize, max_len: usize, capacity: usize) -> Self {
        Self {
            entries: Vec::with_capacity(capacity),
            free_ids: VecDeque::new(),
            num_heads,
            head_dim,
            max_len,
        }
    }

    /// Allocate a new sequence slot and return its index.
    pub fn allocate(&mut self) -> usize {
        if let Some(id) = self.free_ids.pop_front() {
            if id >= self.entries.len() {
                self.entries.push(KVCacheEntry::new(id as u64, self.num_heads, self.head_dim, self.max_len));
            } else {
                self.entries[id] = KVCacheEntry::new(id as u64, self.num_heads, self.head_dim, self.max_len);
            }
            id
        } else {
            let id = self.entries.len();
            self.entries.push(KVCacheEntry::new(id as u64, self.num_heads, self.head_dim, self.max_len));
            id
        }
    }

    /// Free a sequence slot.
    pub fn free(&mut self, id: usize) {
        if let Some(entry) = self.entries.get_mut(id) {
            entry.tokens.clear();
            entry.current_length = 0;
            entry.is_finished = true;
        }
        self.free_ids.push_back(id);
    }

    /// Get a mutable reference to a cache entry.
    pub fn get_mut(&mut self, id: usize) -> Option<&mut KVCacheEntry> {
        self.entries.get_mut(id)
    }

    /// Get an immutable reference to a cache entry.
    pub fn get(&self, id: usize) -> Option<&KVCacheEntry> {
        self.entries.get(id)
    }

    /// Get the number of active (non-finished) sequences.
    pub fn active_count(&self) -> usize {
        self.entries.iter().filter(|e| !e.is_finished && !e.is_empty()).count()
    }

    /// Remove finished sequences and return their IDs.
    pub fn reap_finished(&mut self) -> Vec<u64> {
        let mut reclaimed = Vec::new();
        for (idx, entry) in self.entries.iter_mut().enumerate() {
            if entry.is_finished && !entry.tokens.is_empty() {
                reclaimed.push(entry.sequence_id);
                entry.tokens.clear();
                entry.current_length = 0;
                self.free_ids.push_back(idx);
            }
        }
        reclaimed
    }
}

/// Continuous batching scheduler for transformer inference.
#[derive(Debug, Default)]
pub struct ContinuousBatcher {
    pending_sequences: VecDeque<u64>,
    running_sequences: Vec<u64>,
    max_batch_size: usize,
}

impl ContinuousBatcher {
    /// Create a new continuous batcher.
    pub fn new(max_batch_size: usize) -> Self {
        Self {
            pending_sequences: VecDeque::new(),
            running_sequences: Vec::new(),
            max_batch_size,
        }
    }

    /// Submit a new sequence for inference.
    pub fn submit(&mut self, sequence_id: u64) {
        if !self.running_sequences.contains(&sequence_id) {
            self.pending_sequences.push_back(sequence_id);
        }
    }

    /// Get the next batch of sequences to run.
    pub fn next_batch(&mut self) -> Vec<u64> {
        let mut batch = Vec::with_capacity(self.max_batch_size);

        while batch.len() < self.max_batch_size {
            if let Some(id) = self.pending_sequences.pop_front() {
                batch.push(id);
                self.running_sequences.push(id);
            } else {
                break;
            }
        }

        batch
    }

    /// Mark a sequence as complete and remove it from the running set.
    pub fn complete(&mut self, sequence_id: u64) {
        self.running_sequences.retain(|&id| id != sequence_id);
    }

    /// Get the number of currently running sequences.
    pub fn running_count(&self) -> usize {
        self.running_sequences.len()
    }

    /// Get the number of pending sequences.
    pub fn pending_count(&self) -> usize {
        self.pending_sequences.len()
    }
}

/// Scaled dot-product attention kernel.
///
/// Computes: softmax(Q * K^T / sqrt(d_k)) * V
/// Supports optional FlashAttention-style tiled computation.
pub fn scaled_dot_product_attention(
    q: &[f32],
    k: &[f32],
    v: &[f32],
    num_heads: usize,
    seq_len_q: usize,
    seq_len_kv: usize,
    head_dim: usize,
) -> Vec<f32> {
    let scale = 1.0 / (head_dim as f32).sqrt();
    let mut out = vec![0.0f32; num_heads * seq_len_q * head_dim];

    for h in 0..num_heads {
        for i in 0..seq_len_q {
            let mut max_val = f32::NEG_INFINITY;
            let mut exps = vec![0.0f32; seq_len_kv];
            let mut sum = 0.0f32;

            for j in 0..seq_len_kv {
                let q_offset = h * seq_len_q * head_dim + i * head_dim;
                let k_offset = h * seq_len_kv * head_dim + j * head_dim;
                let mut score = 0.0f32;
                for d in 0..head_dim {
                    score += q[q_offset + d] * k[k_offset + d];
                }
                score *= scale;
                exps[j] = score;
                max_val = max_val.max(score);
            }

            for j in 0..seq_len_kv {
                exps[j] = (exps[j] - max_val).exp();
                sum += exps[j];
            }

            for j in 0..seq_len_kv {
                exps[j] /= sum;
            }

            let out_offset = h * seq_len_q * head_dim + i * head_dim;
            for j in 0..seq_len_kv {
                let v_offset = h * seq_len_kv * head_dim + j * head_dim;
                for d in 0..head_dim {
                    out[out_offset + d] += exps[j] * v[v_offset + d];
                }
            }
        }
    }

    out
}

/// FlashAttention-style tiled attention for memory efficiency.
///
/// Processes attention in tiles to reduce HBM traffic.
/// Falls back to standard SDPA when tile size exceeds limits.
pub fn flash_attention(
    q: &[f32],
    k: &[f32],
    v: &[f32],
    num_heads: usize,
    seq_len_q: usize,
    seq_len_kv: usize,
    head_dim: usize,
    tile_size: usize,
) -> Vec<f32> {
    if tile_size >= seq_len_kv {
        return scaled_dot_product_attention(q, k, v, num_heads, seq_len_q, seq_len_kv, head_dim);
    }

    let scale = 1.0 / (head_dim as f32).sqrt();
    let mut out = vec![0.0f32; num_heads * seq_len_q * head_dim];

    for h in 0..num_heads {
        for i in 0..seq_len_q {
            let mut max_val = f32::NEG_INFINITY;
            let mut sum = 0.0f32;

            for tile_start in (0..seq_len_kv).step_by(tile_size) {
                let tile_end = (tile_start + tile_size).min(seq_len_kv);
                let mut tile_exps = vec![0.0f32; tile_end - tile_start];
                let mut tile_max = f32::NEG_INFINITY;

                let q_offset = h * seq_len_q * head_dim + i * head_dim;

                for j in tile_start..tile_end {
                    let k_offset = h * seq_len_kv * head_dim + j * head_dim;
                    let mut score = 0.0f32;
                    for d in 0..head_dim {
                        score += q[q_offset + d] * k[k_offset + d];
                    }
                    score *= scale;
                    tile_exps[j - tile_start] = score;
                    tile_max = tile_max.max(score);
                }

                let new_max = max_val.max(tile_max);
                let correction = (max_val - new_max).exp();

                for j in tile_start..tile_end {
                    let idx = j - tile_start;
                    tile_exps[idx] = (tile_exps[idx] - new_max).exp();
                    sum = sum * correction + tile_exps[idx];
                }

                for j in tile_start..tile_end {
                    let idx = j - tile_start;
                    let v_offset = h * seq_len_kv * head_dim + j * head_dim;
                    let out_offset = h * seq_len_q * head_dim + i * head_dim;
                    let weight = tile_exps[idx] / sum;
                    for d in 0..head_dim {
                        out[out_offset + d] += weight * v[v_offset + d];
                    }
                }

                max_val = new_max;
            }
        }
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kv_cache_allocate_and_append() {
        let mut mgr = KVCacheManager::new(2, 4, 16, 4);
        let id = mgr.allocate();
        assert_eq!(mgr.active_count(), 0);

        let entry = mgr.get_mut(id).unwrap();
        entry.append_token(1);
        entry.append_token(2);
        assert_eq!(entry.len(), 2);
        assert_eq!(entry.tokens, vec![1, 2]);

        mgr.free(id);
        assert_eq!(mgr.active_count(), 0);
    }

    #[test]
    fn test_continuous_batcher() {
        let mut batcher = ContinuousBatcher::new(2);
        batcher.submit(1);
        batcher.submit(2);
        batcher.submit(3);

        let batch = batcher.next_batch();
        assert_eq!(batch.len(), 2);
        assert_eq!(batch, vec![1, 2]);

        batcher.complete(1);
        let batch2 = batcher.next_batch();
        assert_eq!(batch2.len(), 1);
        assert_eq!(batch2, vec![3]);
    }

    #[test]
    fn test_attention_output_shape() {
        let num_heads = 2;
        let seq_len_q = 4;
        let seq_len_kv = 4;
        let head_dim = 8;

        let q = vec![1.0f32; num_heads * seq_len_q * head_dim];
        let k = vec![1.0f32; num_heads * seq_len_kv * head_dim];
        let v = vec![1.0f32; num_heads * seq_len_kv * head_dim];

        let out = scaled_dot_product_attention(&q, &k, &v, num_heads, seq_len_q, seq_len_kv, head_dim);
        assert_eq!(out.len(), num_heads * seq_len_q * head_dim);
    }

    #[test]
    fn test_flash_attention_fallback() {
        let num_heads = 2;
        let seq_len_q = 2;
        let seq_len_kv = 2;
        let head_dim = 4;

        let q = vec![1.0f32; num_heads * seq_len_q * head_dim];
        let k = vec![1.0f32; num_heads * seq_len_kv * head_dim];
        let v = vec![1.0f32; num_heads * seq_len_kv * head_dim];

        let out_standard = scaled_dot_product_attention(&q, &k, &v, num_heads, seq_len_q, seq_len_kv, head_dim);
        let out_flash = flash_attention(&q, &k, &v, num_heads, seq_len_q, seq_len_kv, head_dim, 4);

        assert_eq!(out_standard.len(), out_flash.len());
        for (a, b) in out_standard.iter().zip(out_flash.iter()) {
            assert!((a - b).abs() < 1e-5);
        }
    }
}
