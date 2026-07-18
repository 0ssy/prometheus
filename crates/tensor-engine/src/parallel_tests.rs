//! Integration-style unit tests for `parallel` (tensor parallelism).
//!
//! Kept in a separate file so they don't bloat `parallel.rs` itself and can
//! be run independently: `cargo test --test parallel_tests`.

use crate::parallel::{partition_bias, partition_linear, all_reduce_sum, tensor_parallel_matmul, TensorParallel};
use crate::Tensor;

fn approx_eq(a: &[f32], b: &[f32], eps: f32) {
    assert_eq!(a.len(), b.len(), "length mismatch: {} vs {}", a.len(), b.len());
    for (i, (&x, &y)) in a.iter().zip(b).enumerate() {
        assert!(
            (x - y).abs() < eps,
            "mismatch at index {i}: {x} vs {y}"
        );
    }
}

// ===========================================================================
// TensorParallel geometry
// ===========================================================================

mod tp_geometry {
    use super::*;

    #[test]
    fn even_split_across_two_devices() {
        let tp = TensorParallel::new(0, 2, "sim:0");
        assert_eq!(tp.row_range(10), 0..5);
        assert_eq!(tp.shard_len(10), 5);

        let tp1 = TensorParallel::new(1, 2, "sim:1");
        assert_eq!(tp1.row_range(10), 5..10);
        assert_eq!(tp1.shard_len(10), 5);
    }

    #[test]
    fn uneven_split_across_three_devices() {
        // 10 across 3 -> [0..4], [4..7], [7..10]
        let cases = [
            (TensorParallel::new(0, 3, "sim:0"), 0usize, 4usize),
            (TensorParallel::new(1, 3, "sim:1"), 4, 7),
            (TensorParallel::new(2, 3, "sim:2"), 7, 10),
        ];
        for (tp, start, end) in cases {
            assert_eq!(tp.row_range(10), start..end, "tp={tp:?}");
            assert_eq!(tp.shard_len(10), end - start);
        }
    }

    #[test]
    fn single_device_gets_everything() {
        let tp = TensorParallel::new(0, 1, "sim:0");
        assert_eq!(tp.row_range(7), 0..7);
        assert_eq!(tp.col_range(5), 0..5);
    }

    #[test]
    fn col_range_mirrors_row_range() {
        let tp = TensorParallel::new(1, 4, "sim:1");
        assert_eq!(tp.row_range(16), 4..8);
        assert_eq!(tp.col_range(16), 4..8);
    }
}

// ===========================================================================
// partition_linear
// ===========================================================================

mod partition_linear_tests {
    use super::*;

    #[test]
    fn splits_columns_evenly() {
        // [2 x 8] split across 4 -> [2 x 2] each
        let w = Tensor::new(vec![2, 8], (0u32..16).map(|x| x as f32).collect());
        for rank in 0..4 {
            let tp = TensorParallel::new(rank, 4, format!("sim:{rank}"));
            let shard = partition_linear(&tp, &w);
            assert_eq!(shard.shape, vec![2, 2]);
        }
    }

    #[test]
    fn shards_are_contiguous_and_non_overlapping() {
        let w = Tensor::new(vec![3, 10], (0..30).map(|x| x as f32).collect());
        let ws = 2;
        let mut prev_end = 0usize;
        for rank in 0..ws {
            let tp = TensorParallel::new(rank, ws, format!("sim:{rank}"));
            let shard = partition_linear(&tp, &w);
            assert!(shard.data.len() > 0);
            assert_eq!(shard.shape[1] + prev_end, tp.row_end(10));
            prev_end += shard.shape[1];
        }
        assert_eq!(prev_end, 10, "all shard columns must sum to out_features");
    }

    #[test]
    fn first_device_starts_at_zero() {
        let w = Tensor::new(vec![2, 6], vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]);
        let tp = TensorParallel::new(0, 3, "sim:0");
        let shard = partition_linear(&tp, &w);
        // rows 0..2, cols 0..2
        assert_eq!(shard, Tensor::new(vec![2, 2], vec![1.0, 2.0, 7.0, 8.0]));
    }

    #[test]
    fn last_device_absorbs_remainder() {
        let w = Tensor::new(vec![2, 7], (0..14).map(|x| x as f32).collect());
        let ws = 3;
        // 7 / 3 -> shards: 3, 2, 2
        let t0 = TensorParallel::new(0, ws, "sim:0");
        let t1 = TensorParallel::new(1, ws, "sim:1");
        let t2 = TensorParallel::new(2, ws, "sim:2");

        let s0 = partition_linear(&t0, &w);
        let s1 = partition_linear(&t1, &w);
        let s2 = partition_linear(&t2, &w);

        assert_eq!(s0.shape[1], 3);
        assert_eq!(s1.shape[1], 2);
        assert_eq!(s2.shape[1], 2);

        // last element (row 0 col 6 = 6.0, row 1 col 6 = 13.0) must be in s2
        assert_eq!(s2.data[s2.data.len() - 2], 6.0);
        assert_eq!(s2.data[s2.data.len() - 1], 13.0);
    }

    #[test]
    fn reconstructs_full_matrix_on_all_reduce() {
        let ws = 3;
        let w = Tensor::new(vec![2, 7], (0..14).map(|x| x as f32).collect());
        let mut reconstructed = vec![vec![]; ws];

        for rank in 0..ws {
            let tp = TensorParallel::new(rank, ws, format!("sim:{rank}"));
            let shard = partition_linear(&tp, &w);
            reconstructed[rank] = shard.data.clone();
        }

        // all_reduce_sum over the shards (treating each shard as one "device" buffer)
        let refs: Vec<&[f32]> = reconstructed.iter().map(|v| v.as_slice()).collect();
        let reduced = all_reduce_sum(&refs);

        // Only one device's output — should equal the original weight
        assert_eq!(reduced[0], w.data);
    }
}

// ===========================================================================
// all_reduce_sum
// ===========================================================================

mod all_reduce_tests {
    use super::*;

    #[test]
    fn single_device_is_identity() {
        let v = vec![10.0f32, 20.0, 30.0];
        let out = all_reduce_sum(&[&v]);
        assert_eq!(out.len(), 1);
        assert_eq!(out[0], v);
    }

    #[test]
    fn sums_element_wise_across_two_devices() {
        let a = vec![1.0f32, 0.0, 0.0];
        let b = vec![0.0f32, 1.0, 0.0];
        let out = all_reduce_sum(&[&a, &b]);
        assert_eq!(out, vec![vec![1.0, 1.0, 0.0], vec![1.0, 1.0, 0.0]]);
    }

    #[test]
    fn sums_element_wise_across_four_devices() {
        let inputs: Vec<Vec<f32>> = (0..4)
            .map(|i| vec![i as f32; 5])
            .collect();
        let refs: Vec<&[f32]> = inputs.iter().map(|v| v.as_slice()).collect();
        let out = all_reduce_sum(&refs);
        let expected_sum: f32 = (0..4).map(|i| i as f32).sum();
        let expected = vec![expected_sum; 5];
        assert_eq!(out, vec![expected.clone(); 4]);
    }

    #[test]
    fn result_identical_on_all_participants() {
        let d0 = vec![3.0f32, 7.0];
        let d1 = vec![1.0f32, 2.0];
        let d2 = vec![4.0f32, 5.0];
        let out = all_reduce_sum(&[&d0, &d1, &d2]);
        assert_eq!(out[0], out[1]);
        assert_eq!(out[1], out[2]);
    }

    #[test]
    fn empty_buffer_per_device() {
        let d0: Vec<f32> = vec![];
        let d1: Vec<f32> = vec![];
        let out = all_reduce_sum(&[&d0, &d1]);
        assert_eq!(out, vec![vec![], vec![]]);
    }

    #[test]
    #[should_panic]
    fn mismatched_lengths_panic() {
        all_reduce_sum(&[&[1.0f32, 2.0f32][..], &[1.0f32, 2.0f32, 3.0f32][..]]);
    }
}

// ===========================================================================
// tensor_parallel_matmul
// ===========================================================================

mod tp_matmul_tests {
    use super::*;

    #[test]
    fn world_size_1_matches_plain_matmul() {
        let tp = TensorParallel::new(0, 1, "sim:0");
        let a = Tensor::new(vec![2, 3], vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0]);
        let b = Tensor::new(vec![3, 2], vec![7.0, 8.0, 9.0, 10.0, 11.0, 12.0]);

        let result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);
        assert_eq!(result.shape, expected.shape);
        approx_eq(&result.data, &expected.data, 1e-5);
    }

    #[test]
    fn world_size_2_square_matrices() {
        let tp = TensorParallel::new(0, 2, "sim:0");
        let a = Tensor::new(vec![4, 4], vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
                                               9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]);
        let b = Tensor::new(vec![4, 4], vec![1.0, 0.0, 0.0, 0.0,
                                               0.0, 1.0, 0.0, 0.0,
                                               0.0, 0.0, 1.0, 0.0,
                                               0.0, 0.0, 0.0, 1.0]);

        let result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);
        approx_eq(&result.data, &expected.data, 1e-4);
    }

    #[test]
    fn world_size_4_rectangular() {
        let tp = TensorParallel::new(0, 4, "sim:0");
        // [2 x 8] @ [8 x 3]
        let a = Tensor::new(vec![2, 8], (0..16).map(|x| x as f32).collect());
        let b = Tensor::new(vec![8, 3], (0..24).map(|x| x as f32).collect());

        let result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);
        approx_eq(&result.data, &expected.data, 1e-4);
    }

    #[test]
    fn world_size_3_uneven_inner_dim() {
        let tp = TensorParallel::new(0, 3, "sim:0");
        // [5 x 10] @ [10 x 4]  -> inner dim 10 splits 4, 3, 3
        let a = Tensor::new(vec![5, 10], (0..50).map(|x| x as f32).collect());
        let b = Tensor::new(vec![10, 4], (0..40).map(|x| x as f32).collect());

        let result = tensor_parallel_matmul(&tp, &a, &b);
        let expected = a.matmul(&b);
        approx_eq(&result.data, &expected.data, 1e-4);
    }

    #[test]
    fn matmul_result_shape_is_m_by_n() {
        let tp = TensorParallel::new(0, 2, "sim:0");
        let a = Tensor::new(vec![7, 5], vec![1.0; 35]);
        let b = Tensor::new(vec![5, 3], vec![2.0; 15]);
        let result = tensor_parallel_matmul(&tp, &a, &b);
        assert_eq!(result.shape, vec![7, 3]);
    }

    #[test]
    fn each_rank_gets_same_result() {
        // We can't easily test real inter-device communication, but we can
        // verify that every simulated rank produces the same output for a
        // given (a, b) by calling the function with different `device_id`s.
        let a = Tensor::new(vec![3, 6], (0..18).map(|x| x as f32).collect());
        let b = Tensor::new(vec![6, 4], (0..24).map(|x| x as f32).collect());

        let ws = 4;
        let mut first_result: Option<Vec<f32>> = None;
        for rank in 0..ws {
            let tp = TensorParallel::new(rank, ws, format!("sim:{rank}"));
            let result = tensor_parallel_matmul(&tp, &a, &b);
            match &first_result {
                None => first_result = Some(result.data.clone()),
                Some(expected) => approx_eq(&result.data, expected, 1e-4),
            }
        }
    }
}

// ===========================================================================
// partition_bias
// ===========================================================================

mod bias_tests {
    use super::*;

    #[test]
    fn splits_1d_bias_evenly() {
        let tp = TensorParallel::new(1, 2, "sim:1");
        let bias = Tensor::new(vec![6], vec![0.0, 1.0, 2.0, 3.0, 4.0, 5.0]);
        let shard = partition_bias(&tp, &bias);
        assert_eq!(shard, Tensor::new(vec![3], vec![3.0, 4.0, 5.0]));
    }

    #[test]
    fn splits_1d_bias_unevenly() {
        // 7 elements across 3 -> 3, 2, 2
        let bias = Tensor::new(vec![7], vec![10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]);
        let t2 = TensorParallel::new(2, 3, "sim:2");
        let shard = partition_bias(&t2, &bias);
        assert_eq!(shard, Tensor::new(vec![2], vec![60.0, 70.0]));
    }

    #[test]
    #[should_panic(expected = "partition_bias requires 1-D bias")]
    fn rejects_2d_bias() {
        let tp = TensorParallel::new(0, 1, "sim:0");
        let bias = Tensor::new(vec![2, 2], vec![1.0, 2.0, 3.0, 4.0]);
        let _ = partition_bias(&tp, &bias);
    }
}

// ===========================================================================
// Cross-cutting: partition + matmul round-trip
// ===========================================================================

#[test]
fn partitioned_weight_shard_can_do_matmul_with_full_input() {
    // Simulate the standard "column-parallel linear" pattern:
    //   1. full A [M x K]
    //   2. weight shards [K x K/ws]
    //   3. local matmul gives [M x K/ws]
    //   4. all-reduce merges to [M x K]
    //   5. add column-parallel bias
    let ws = 2;
    let k = 6;
    let m = 3;
    let a = Tensor::new(vec![m, k], (0..(m * k)).map(|x| x as f32).collect());

    // Full weight
    let w = Tensor::new(vec![k, k], (0..(k * k)).map(|x| x as f32).collect());
    let bias = Tensor::new(vec![k], (0..k).map(|x| x as f32).collect());

    // Compute the expected result with a full (non-parallel) linear layer
    let expected = a.matmul(&w);
    let expected = expected.add(&Tensor::new(vec![m, k], bias.data.clone()));

    // Simulate each device's computation
    let mut partials = Vec::with_capacity(ws);
    for rank in 0..ws {
        let tp = TensorParallel::new(rank, ws, format!("sim:{rank}"));
        let w_shard = partition_linear(&tp, &w);
        let b_shard = partition_bias(&tp, &bias);
        let local = a.matmul(&w_shard);
        let local = local.add_scalar(b_shard.data[0]); // bias has 1 element per shard
        partials.push(local.data);
    }

    // All-reduce
    let refs: Vec<&[f32]> = partials.iter().map(|v| v.as_slice()).collect();
    let reduced = all_reduce_sum(&refs);

    // The all-reduced result should equal the full (a @ W + bias) computation
    approx_eq(&reduced[0], &expected.data, 1e-4);
}
