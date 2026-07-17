//! P5 Titan CUDA backend — FFI bindings to `tensor_cuda.cu`.
//!
//! Compiled only when the `cuda` feature is enabled and `nvcc` is available.

#[cfg(feature = "cuda")]
mod cuda_impl {
    extern "C" {
        fn cuda_tensor_add(
            h_a: *const f32,
            h_b: *const f32,
            h_out: *mut f32,
            n: usize,
        ) -> i32;

        fn cuda_matmul(
            h_a: *const f32,
            h_b: *const f32,
            h_c: *mut f32,
            m: i32,
            k: i32,
            n: i32,
        ) -> i32;

        fn cuda_softmax(h_x: *mut f32, rows: i32, cols: i32) -> i32;
    }

    pub fn add(a: &[f32], b: &[f32]) -> Vec<f32> {
        assert_eq!(a.len(), b.len());
        let mut out = vec![0.0f32; a.len()];
        let rc = unsafe {
            cuda_tensor_add(a.as_ptr(), b.as_ptr(), out.as_mut_ptr(), a.len())
        };
        if rc != 0 {
            panic!("CUDA add failed with code {rc}");
        }
        out
    }

    pub fn matmul(a: &[f32], b: &[f32], m: i32, k: i32, n: i32) -> Vec<f32> {
        let mut out = vec![0.0f32; (m * n) as usize];
        let rc = unsafe {
            cuda_matmul(a.as_ptr(), b.as_ptr(), out.as_mut_ptr(), m, k, n)
        };
        if rc != 0 {
            panic!("CUDA matmul failed with code {rc}");
        }
        out
    }

    pub fn softmax(x: &mut [f32], rows: i32, cols: i32) {
        let rc = unsafe { cuda_softmax(x.as_mut_ptr(), rows, cols) };
        if rc != 0 {
            panic!("CUDA softmax failed with code {rc}");
        }
    }
}

#[cfg(not(feature = "cuda"))]
mod cuda_impl {
    pub fn add(a: &[f32], b: &[f32]) -> Vec<f32> {
        a.iter().zip(b.iter()).map(|(&x, &y)| x + y).collect()
    }

    pub fn matmul(a: &[f32], b: &[f32], m: i32, k: i32, n: i32) -> Vec<f32> {
        let mut out = vec![0.0f32; (m * n) as usize];
        for i in 0..m {
            for j in 0..n {
                let mut acc = 0.0;
                for kk in 0..k {
                    acc += a[(i * k + kk) as usize] * b[(kk * n + j) as usize];
                }
                out[(i * n + j) as usize] = acc;
            }
        }
        out
    }

    pub fn softmax(x: &mut [f32], rows: i32, cols: i32) {
        let rows = rows as usize;
        let cols = cols as usize;
        for r in 0..rows {
            let start = r * cols;
            let end = start + cols;
            let row = &mut x[start..end];
            let max_val = row.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
            let exps: Vec<f32> = row.iter().map(|&v| (v - max_val).exp()).collect();
            let sum: f32 = exps.iter().sum();
            for (i, &v) in exps.iter().enumerate() {
                row[i] = v / sum;
            }
        }
    }
}

pub use cuda_impl::{add, matmul, softmax};
