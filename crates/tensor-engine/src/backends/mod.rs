//! Backend abstraction for tensor operations.
//!
//! Each backend module exposes the same operation signatures but may
//! dispatch to CPU scalar, SIMD, CUDA, or WGPU compute paths.

pub use crate::cuda;
pub mod simd;
pub mod wgpu;

pub use cuda::{add as cuda_add, matmul as cuda_matmul, softmax as cuda_softmax};
pub use simd::{add as simd_add, mul as simd_mul, add_scalar as simd_add_scalar, mul_scalar as simd_mul_scalar};
pub use wgpu::wgpu_backend::{add as wgpu_add, mul as wgpu_mul, matmul as wgpu_matmul};

/// Backend dispatch enum for runtime selection.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Backend {
    Cpu,
    Simd,
    Cuda,
    Wgpu,
}

impl Backend {
    pub fn as_str(&self) -> &'static str {
        match self {
            Backend::Cpu => "cpu",
            Backend::Simd => "simd",
            Backend::Cuda => "cuda",
            Backend::Wgpu => "wgpu",
        }
    }
}
