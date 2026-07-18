//! Phase 7.4 — Model Partitioning & Tensor Parallelism.
//!
//! Splits linear-layer weight matrices across N devices, runs sharded matmuls
//! locally, and merges partial results via a ring-all-reduce simulation.
//!
//! Feature-gated behind `tensor-parallel` to avoid pulling in any extra deps
//! for users that don't need distributed inference.

use crate::Tensor;

/// Metadata for one participant in a tensor-parallel group.
///
/// `device_id` is a zero-based rank in `[0, world_size)`.
/// `world_size` is the total number of devices sharing a single model layer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TensorParallel {
    /// Zero-based device/rank identifier.
    pub device_id: usize,
    /// Total number of devices in the parallel group.
    pub world_size: usize,
    /// Human-readable label (e.g. "cuda:0", "cpu:1").
    pub label: String,
}

impl TensorParallel {
    /// Create a new `TensorParallel` handle.
    ///
    /// # Panics
    ///
    /// Panics if `device_id >= world_size` or `world_size == 0`.
    pub fn new(device_id: usize, world_size: usize, label: impl Into<String>) -> Self {
        assert!(world_size > 0, "world_size must be > 0");
        assert!(device_id < world_size, "device_id must be < world_size");
        Self { device_id, world_size, label: label.into() }
    }

    /// Size of this device's shard along a dimension split into `world_size`
    /// equal (or near-equal) pieces.
    pub fn shard_size(&self, total: usize) -> usize {
        let base = total / self.world_size;
        let remainder = total % self.world_size;
        if self.device_id < remainder {
            base + 1
        } else {
            base
        }
    }

    /// Starting row index (inclusive) of this device's shard when splitting
    /// a matrix with `total` rows along the first axis.
    pub fn row_start(&self, total: usize) -> usize {
        let base = total / self.world_size;
        let remainder = total % self.world_size;
        self.device_id * base + self.device_id.min(remainder)
    }

    /// Ending row index (exclusive) of this device's shard.
    pub fn row_end(&self, total: usize) -> usize {
        self.row_start(total) + self.shard_size(total)
    }

    /// Slice of row indices owned by this device for a `total`-row matrix.
    pub fn row_range(&self, total: usize) -> std::ops::Range<usize> {
        self.row_start(total)..self.row_end(total)
    }

    /// Starting col index (inclusive) when splitting a matrix with `total`
    /// columns across devices.
    pub fn col_start(&self, total: usize) -> usize {
        self.row_start(total) // same arithmetic, different semantic
    }

    /// Ending col index (exclusive).
    pub fn col_end(&self, total: usize) -> usize {
        self.row_end(total)
    }

    /// Slice of col indices owned by this device for a `total`-col matrix.
    pub fn col_range(&self, total: usize) -> std::ops::Range<usize> {
        self.col_start(total)..self.col_end(total)
    }

    /// Shard size for a given `total` along a partition axis.
    pub fn shard_len(&self, total: usize) -> usize {
        self.row_end(total) - self.row_start(total)
    }
}

// ---------------------------------------------------------------------------
// Weight partitioning
// ---------------------------------------------------------------------------

/// Split a 2-D weight matrix `[in_features x out_features]` across `world_size`
/// devices by **rows** (each device owns a contiguous block of input channels).
///
/// Returns the shard owned by `tp.device_id`.
///
/// # Panics
///
/// Panics if `weight` is not 2-D or `out_features` is not evenly divisible by
/// `world_size` (we allow a remainder of at most 1 — the last device absorbs it).
pub fn partition_linear(tp: &TensorParallel, weight: &Tensor) -> Tensor {
    assert_eq!(weight.shape.len(), 2, "partition_linear requires 2-D weight");
    let [in_features, out_features] = weight.shape.as_slice() else { unreachable!() };
    let r = tp.row_range(*out_features);
    let shard_cols = r.end - r.start;

    let mut shard_data = Vec::with_capacity(in_features * shard_cols);
    for row in 0..*in_features {
        let row_offset = row * out_features;
        shard_data.extend_from_slice(&weight.data[row_offset + r.start..row_offset + r.end]);
    }

    Tensor::new(vec![*in_features, shard_cols], shard_data)
}

// ---------------------------------------------------------------------------
// Ring all-reduce (simulated, single-threaded)
// ---------------------------------------------------------------------------

/// Simulate ring-all-reduce across `world_size` devices for a flat `f32` slice.
///
/// In a real implementation each device would exchange data over a network;
/// here we gather every device's input into a single vector, sum element-wise,
/// and return the result for **every** participant.  This is the mathematical
/// equivalent of all-reduce with the `SUM` operator, and is used to validate
/// that sharded matmul partials sum correctly.
///
/// `inputs` is indexed by device rank — `inputs[device_id]` is that device's
/// local buffer.  All buffers must have the same length.
///
/// Returns a `Vec<Vec<f32>>` where each entry is the full reduced result
/// (identical across all devices).
pub fn all_reduce_sum(inputs: &[&[f32]]) -> Vec<Vec<f32>> {
    assert!(!inputs.is_empty(), "all_reduce_sum needs at least one device");
    let len = inputs[0].len();
    for (i, s) in inputs.iter().enumerate() {
        assert_eq!(s.len(), len, "device {i} has mismatched buffer length {len} vs {}", s.len());
    }

    let mut reduced = vec![0.0f32; len];
    for s in inputs {
        for (r, &v) in reduced.iter_mut().zip(*s) {
            *r += v;
        }
    }

    // Every device receives the same full result.
    vec![reduced.clone(); inputs.len()]
}

// ---------------------------------------------------------------------------
// Sharded matrix multiply
// ---------------------------------------------------------------------------

/// Run a **tensor-parallel matrix multiply**:
///
/// ```text
///   A: [M x K]   — rows partitioned across devices
///   B: [K x N]   — columns partitioned across devices
///
/// Each device computes its local partial:
///   partial_i = A_i @ B_i          (A_i is [M x K_i], B_i is [K_i x N])
///
/// Then all devices all-reduce (SUM) their partials to obtain the full [M x N]
/// result.
/// ```
///
/// # Arguments
///
/// * `tp` — tensor-parallel context for this device.
/// * `a` — left-hand matrix, **not** sharded (the full matrix is passed to
///   every device; only the result is sharded in a real system — here we
///   simulate by slicing rows internally to mirror what would arrive at this
///   device).
/// * `b` — right-hand matrix, **not** sharded (same rationale as `a`).
///
/// # Returns
///
/// The full `[M x N]` result (all-reduced across all simulated devices).
///
/// # Panics
///
/// Panics on shape mismatch.
pub fn tensor_parallel_matmul(tp: &TensorParallel, a: &Tensor, b: &Tensor) -> Tensor {
    // --- validate ----------------------------------------------------------
    let &[m, k_a] = a.shape.as_slice() else { panic!("tensor_parallel_matmul: A must be 2-D") };
    let &[k_b, n] = b.shape.as_slice() else { panic!("tensor_parallel_matmul: B must be 2-D") };
    assert_eq!(k_a, k_b, "tensor_parallel_matmul: inner dims must match ({k_a} vs {k_b})");

    let ws = tp.world_size;

    // --- build per-device partials -----------------------------------------
    // Each device owns a contiguous row block of A and col block of B.
    // For the simulation each device slices the *full* A/B it has access to.
    let a_range = tp.row_range(k_a);
    let b_range = tp.row_range(k_b); // split B along its K rows

    // Slice A: all M rows, only a_range of K columns  -> [M x K_shard]
    let mut a_shard_data = Vec::with_capacity(m * a_range.len());
    for row in 0..m {
        let base = row * k_a;
        a_shard_data.extend_from_slice(&a.data[base + a_range.start..base + a_range.end]);
    }
    let a_shard = Tensor::new(vec![m, a_range.len()], a_shard_data);

    // Slice B: only b_range of K rows, all N cols        -> [K_shard x N]
    let mut b_shard_data = Vec::with_capacity(b_range.len() * n);
    for row in b_range.clone() {
        let base = row * n;
        b_shard_data.extend_from_slice(&b.data[base..base + n]);
    }
    let b_shard = Tensor::new(vec![b_range.len(), n], b_shard_data);

    // Local matmul -> partial [M x N]
    let _partial = a_shard.matmul(&b_shard);

    // --- simulate all-reduce across all devices -----------------------------
    // We need every device's partial to compute the real all-reduce.
    // We compute them all here (in a real system each device would do this
    // independently and then communicate).
    let all_partials: Vec<Vec<f32>> = (0..ws)
        .map(|rank| {
            let dev = TensorParallel::new(rank, ws, format!("sim:{rank}"));
            let ar = dev.row_range(k_a);
            let br = dev.row_range(k_b);

            let mut ad = Vec::with_capacity(m * ar.len());
            for row in 0..m {
                let base = row * k_a;
                ad.extend_from_slice(&a.data[base + ar.start..base + ar.end]);
            }
            let a_s = Tensor::new(vec![m, ar.len()], ad);

            let mut bd = Vec::with_capacity(br.len() * n);
            for row in br.clone() {
                let base = row * n;
                bd.extend_from_slice(&b.data[base..base + n]);
            }
            let b_s = Tensor::new(vec![br.len(), n], bd);

            a_s.matmul(&b_s).data
        })
        .collect();

    // all_reduce_sum expects &[&[f32]]
    let refs: Vec<&[f32]> = all_partials.iter().map(|v| v.as_slice()).collect();
    let reduced = all_reduce_sum(&refs);

    // Every device got the same result; return the full matrix.
    Tensor::new(vec![m, n], reduced[0].clone())
}

// ---------------------------------------------------------------------------
// Convenience helpers
// ---------------------------------------------------------------------------

/// Partition a 1-D bias vector across devices by contiguous chunks.
/// Returns the shard for `tp.device_id`.
pub fn partition_bias(tp: &TensorParallel, bias: &Tensor) -> Tensor {
    assert_eq!(bias.shape.len(), 1, "partition_bias requires 1-D bias");
    let total = bias.shape[0];
    let r = tp.row_range(total);
    Tensor::new(vec![r.len()], bias.data[r.start..r.end].to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;

    // -----------------------------------------------------------------------
    // TensorParallel geometry
    // -----------------------------------------------------------------------

    #[test]
    fn tp_row_range_even_split() {
        let tp = TensorParallel::new(0, 2, "cpu:0");
        // 8 rows split across 2 devices -> 4 each
        assert_eq!(tp.row_range(8), 0..4);
        let tp1 = TensorParallel::new(1, 2, "cpu:1");
        assert_eq!(tp1.row_range(8), 4..8);
    }

    #[test]
    fn tp_row_range_uneven_split() {
        // 7 rows across 3 devices -> [0..3], [3..5], [5..7]
        let t0 = TensorParallel::new(0, 3, "cpu:0");
        assert_eq!(t0.row_range(7), 0..3);
        let t1 = TensorParallel::new(1, 3, "cpu:1");
        assert_eq!(t1.row_range(7), 3..5);
        let t2 = TensorParallel::new(2, 3, "cpu:2");
        assert_eq!(t2.row_range(7), 5..7);
    }

    #[test]
    #[should_panic(expected = "device_id must be < world_size")]
    fn tp_rejects_invalid_device_id() {
        TensorParallel::new(5, 2, "bad");
    }

    #[test]
    #[should_panic(expected = "world_size must be > 0")]
    fn tp_rejects_zero_world_size() {
        TensorParallel::new(0, 0, "bad");
    }

    // -----------------------------------------------------------------------
    // partition_linear
    // -----------------------------------------------------------------------

    #[test]
    fn partition_linear_even() {
        // weight [4 x 6], world_size=2 -> each shard [4 x 3]
        let tp = TensorParallel::new(0, 2, "cpu:0");
        let w = Tensor::new(vec![4, 6], (0..24).map(|x| x as f32).collect());

        let shard = partition_linear(&tp, &w);
        assert_eq!(shard.shape, vec![4, 3]);

        // First 3 cols of every row
        let expected_row0: Vec<f32> = (0..3).map(|x| x as f32).collect();
        assert_eq!(&shard.data[0..3], expected_row0.as_slice());

        // Second device
        let tp1 = TensorParallel::new(1, 2, "cpu:1");
        let shard1 = partition_linear(&tp1, &w);
        assert_eq!(shard1.shape, vec![4, 3]);
        let expected_row0_1: Vec<f32> = (3..6).map(|x| x as f32).collect();
        assert_eq!(&shard1.data[0..3], expected_row0_1.as_slice());
    }

    #[test]
    fn partition_linear_uneven() {
        // weight [3 x 7], world_size=3 -> shards [3 x 3], [3 x 2], [3 x 2]
        let w = Tensor::new(vec![3, 7], (0..21).map(|x| x as f32).collect());

        let t0 = TensorParallel::new(0, 3, "cpu:0");
        let s0 = partition_linear(&t0, &w);
        assert_eq!(s0.shape, vec![3, 3]);

        let t1 = TensorParallel::new(1, 3, "cpu:1");
        let s1 = partition_linear(&t1, &w);
        assert_eq!(s1.shape, vec![3, 2]);

        let t2 = TensorParallel::new(2, 3, "cpu:2");
        let s2 = partition_linear(&t2, &w);
        assert_eq!(s2.shape, vec![3, 2]);
    }

    // -----------------------------------------------------------------------
    // partition_bias
    // -----------------------------------------------------------------------

    #[test]
    fn partition_bias_even() {
        let tp = TensorParallel::new(0, 2, "cpu:0");
        let bias = Tensor::new(vec![6], vec![0.0, 1.0, 2.0, 3.0, 4.0, 5.0]);
        let shard = partition_bias(&tp, &bias);
        assert_eq!(shard, Tensor::new(vec![3], vec![0.0, 1.0, 2.0]));
    }

    // -----------------------------------------------------------------------
    // all_reduce_sum
    // -----------------------------------------------------------------------

    #[test]
    fn all_reduce_sum_single_device() {
        let data = vec![1.0f32, 2.0, 3.0];
        let result = all_reduce_sum(&[&data]);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0], vec![1.0, 2.0, 3.0]);
    }

    #[test]
    fn all_reduce_sum_two_devices() {
        let d0 = vec![1.0f32, 0.0, 0.0];
        let d1 = vec![0.0, 2.0, 0.0];
        let result = all_reduce_sum(&[&d0, &d1]);
        assert_eq!(result.len(), 2);
        assert_eq!(result[0], vec![1.0, 2.0, 0.0]);
        assert_eq!(result[1], vec![1.0, 2.0, 0.0]);
    }

    #[test]
    fn all_reduce_sum_three_devices() {
        let d0 = vec![1.0f32, 1.0];
        let d1 = vec![2.0f32, 3.0];
        let d2 = vec![4.0f32, 5.0];
        let result = all_reduce_sum(&[&d0, &d1, &d2]);
        assert_eq!(result, vec![vec![7.0, 9.0], vec![7.0, 9.0], vec![7.0, 9.0]]);
    }

    #[test]
    fn all_reduce_sum_panics_on_mismatched_lengths() {
        let d0 = vec![1.0f32, 2.0];
        let d1 = vec![1.0f32];
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            all_reduce_sum(&[&d0, &d1])
        }));
        assert!(result.is_err());
    }

    #[test]
    fn all_reduce_sum_panics_on_empty_inputs() {
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            all_reduce_sum(&[] as &[&[f32]])
        }));
        assert!(result.is_err());
    }

    // -----------------------------------------------------------------------
    // tensor_parallel_matmul
    // -----------------------------------------------------------------------

    #[test]
    fn tp_matmul_equals_regular_matmul_world_size_1() {
        // world_size=1 should be identical to a plain matmul
        let tp = TensorParallel::new(0, 1, "cpu:0");
        let a = Tensor::new(vec![2, 3], vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0]);
        let b = Tensor::new(vec![3, 2], vec![7.0, 8.0, 9.0, 10.0, 11.0, 12.0]);

        let tp_result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);

        assert_eq!(tp_result.shape, expected.shape);
        assert_eq!(tp_result.data, expected.data);
    }

    #[test]
    fn tp_matmul_equals_regular_matmul_world_size_2() {
        let tp = TensorParallel::new(0, 2, "cpu:0");
        // [4 x 8] @ [8 x 3]
        let a = Tensor::new(vec![4, 8], (0..32).map(|x| x as f32).collect());
        let b = Tensor::new(vec![8, 3], (0..24).map(|x| x as f32).collect());

        let tp_result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);

        assert_eq!(tp_result.shape, vec![4, 3]);
        for (i, (&got, &exp)) in tp_result.data.iter().zip(&expected.data).enumerate() {
            assert!(
                (got - exp).abs() < 1e-4,
                "mismatch at index {i}: got {got}, expected {exp}"
            );
        }
    }

    #[test]
    fn tp_matmul_equals_regular_matmul_world_size_4() {
        let tp = TensorParallel::new(0, 4, "cpu:0");
        // [2 x 12] @ [12 x 5]
        let a = Tensor::new(vec![2, 12], (0..24).map(|x| x as f32).collect());
        let b = Tensor::new(vec![12, 5], (0..60).map(|x| x as f32).collect());

        let tp_result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);

        assert_eq!(tp_result.shape, vec![2, 5]);
        for (i, (&got, &exp)) in tp_result.data.iter().zip(&expected.data).enumerate() {
            assert!(
                (got - exp).abs() < 1e-4,
                "mismatch at index {i}: got {got}, expected {exp}"
            );
        }
    }

    #[test]
    fn tp_matmul_uneven_inner_dim() {
        // [3 x 10] @ [10 x 4], world_size=3 -> inner dim splits 4,3,3
        let tp = TensorParallel::new(0, 3, "cpu:0");
        let a = Tensor::new(vec![3, 10], (0..30).map(|x| x as f32).collect());
        let b = Tensor::new(vec![10, 4], (0..40).map(|x| x as f32).collect());

        let tp_result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);

        assert_eq!(tp_result.shape, vec![3, 4]);
        for (i, (&got, &exp)) in tp_result.data.iter().zip(&expected.data).enumerate() {
            assert!(
                (got - exp).abs() < 1e-4,
                "mismatch at index {i}: got {got}, expected {exp}"
            );
        }
    }

    #[test]
    fn tp_matmul_identity_like() {
        // A @ I should equal A
        let tp = TensorParallel::new(0, 2, "cpu:0");
        let a = Tensor::new(vec![3, 4], vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]);
        let identity = Tensor::new(vec![4, 4], vec![1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]);

        let result = tensor_parallel_matmul(&tp, &a, &identity);
        for (i, (&got, &exp)) in result.data.iter().zip(&a.data).enumerate() {
            assert!(
                (got - exp).abs() < 1e-4,
                "identity mismatch at {i}: {got} vs {exp}"
            );
        }
    }
}
