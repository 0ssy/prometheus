//! SIMD-accelerated tensor backend using `std::arch`.
//!
//! Uses x86_64 SSE/AVX and AArch64 NEON intrinsics for vectorized operations.

#[cfg(all(feature = "simd", any(target_arch = "x86_64", target_arch = "aarch64")))]
pub mod simd_backend {
    #[cfg(target_arch = "x86_64")]
    use std::arch::x86_64::*;

    #[cfg(target_arch = "aarch64")]
    use std::arch::aarch64::*;

    /// Element-wise add using SIMD.
    pub fn add(a: &[f32], b: &[f32]) -> Vec<f32> {
        assert_eq!(a.len(), b.len());
        let len = a.len();
        let mut out = Vec::with_capacity(len);

        #[cfg(target_arch = "x86_64")]
        {
            let chunks = len / 8;
            let remainder = len % 8;

            for i in 0..chunks {
                let idx = i * 8;
                unsafe {
                    let va = _mm256_loadu_ps(a.as_ptr().add(idx));
                    let vb = _mm256_loadu_ps(b.as_ptr().add(idx));
                    let vc = _mm256_add_ps(va, vb);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }
            }

            if remainder > 0 {
                let idx = chunks * 8;
                unsafe {
                    let mut va_arr = [0.0f32; 8];
                    let mut vb_arr = [0.0f32; 8];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    vb_arr[..remainder].copy_from_slice(&b[idx..]);
                    let va = _mm256_loadu_ps(va_arr.as_ptr());
                    let vb = _mm256_loadu_ps(vb_arr.as_ptr());
                    let vc = _mm256_add_ps(va, vb);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        #[cfg(target_arch = "aarch64")]
        {
            let chunks = len / 4;
            let remainder = len % 4;

            for i in 0..chunks {
                let idx = i * 4;
                unsafe {
                    let va = vld1q_f32(a.as_ptr().add(idx));
                    let vb = vld1q_f32(b.as_ptr().add(idx));
                    let vc = vaddq_f32(va, vb);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }
            }

            if remainder > 0 {
                let idx = chunks * 4;
                unsafe {
                    let mut va_arr = [0.0f32; 4];
                    let mut vb_arr = [0.0f32; 4];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    vb_arr[..remainder].copy_from_slice(&b[idx..]);
                    let va = vld1q_f32(va_arr.as_ptr());
                    let vb = vld1q_f32(vb_arr.as_ptr());
                    let vc = vaddq_f32(va, vb);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        out
    }

    /// Element-wise multiply using SIMD.
    pub fn mul(a: &[f32], b: &[f32]) -> Vec<f32> {
        assert_eq!(a.len(), b.len());
        let len = a.len();
        let mut out = Vec::with_capacity(len);

        #[cfg(target_arch = "x86_64")]
        {
            let chunks = len / 8;
            let remainder = len % 8;

            for i in 0..chunks {
                let idx = i * 8;
                unsafe {
                    let va = _mm256_loadu_ps(a.as_ptr().add(idx));
                    let vb = _mm256_loadu_ps(b.as_ptr().add(idx));
                    let vc = _mm256_mul_ps(va, vb);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }
            }

            if remainder > 0 {
                let idx = chunks * 8;
                unsafe {
                    let mut va_arr = [0.0f32; 8];
                    let mut vb_arr = [0.0f32; 8];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    vb_arr[..remainder].copy_from_slice(&b[idx..]);
                    let va = _mm256_loadu_ps(va_arr.as_ptr());
                    let vb = _mm256_loadu_ps(vb_arr.as_ptr());
                    let vc = _mm256_mul_ps(va, vb);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        #[cfg(target_arch = "aarch64")]
        {
            let chunks = len / 4;
            let remainder = len % 4;

            for i in 0..chunks {
                let idx = i * 4;
                unsafe {
                    let va = vld1q_f32(a.as_ptr().add(idx));
                    let vb = vld1q_f32(b.as_ptr().add(idx));
                    let vc = vmulq_f32(va, vb);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }
            }

            if remainder > 0 {
                let idx = chunks * 4;
                unsafe {
                    let mut va_arr = [0.0f32; 4];
                    let mut vb_arr = [0.0f32; 4];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    vb_arr[..remainder].copy_from_slice(&b[idx..]);
                    let va = vld1q_f32(va_arr.as_ptr());
                    let vb = vld1q_f32(vb_arr.as_ptr());
                    let vc = vmulq_f32(va, vb);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        out
    }

    /// Scalar addition (broadcasted) using SIMD.
    pub fn add_scalar(a: &[f32], scalar: f32) -> Vec<f32> {
        let len = a.len();
        let mut out = Vec::with_capacity(len);

        #[cfg(target_arch = "x86_64")]
        {
            let chunks = len / 8;
            let remainder = len % 8;
            unsafe {
                let vs = _mm256_set1_ps(scalar);

                for i in 0..chunks {
                    let idx = i * 8;
                    let va = _mm256_loadu_ps(a.as_ptr().add(idx));
                    let vc = _mm256_add_ps(va, vs);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }

                if remainder > 0 {
                    let idx = chunks * 8;
                    let mut va_arr = [0.0f32; 8];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    let va = _mm256_loadu_ps(va_arr.as_ptr());
                    let vc = _mm256_add_ps(va, vs);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        #[cfg(target_arch = "aarch64")]
        {
            let chunks = len / 4;
            let remainder = len % 4;
            unsafe {
                let vs = vdupq_n_f32(scalar);

                for i in 0..chunks {
                    let idx = i * 4;
                    let va = vld1q_f32(a.as_ptr().add(idx));
                    let vc = vaddq_f32(va, vs);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }

                if remainder > 0 {
                    let idx = chunks * 4;
                    let mut va_arr = [0.0f32; 4];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    let va = vld1q_f32(va_arr.as_ptr());
                    let vc = vaddq_f32(va, vs);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        out
    }

    /// Scalar multiplication (broadcasted) using SIMD.
    pub fn mul_scalar(a: &[f32], scalar: f32) -> Vec<f32> {
        let len = a.len();
        let mut out = Vec::with_capacity(len);

        #[cfg(target_arch = "x86_64")]
        {
            let chunks = len / 8;
            let remainder = len % 8;
            unsafe {
                let vs = _mm256_set1_ps(scalar);

                for i in 0..chunks {
                    let idx = i * 8;
                    let va = _mm256_loadu_ps(a.as_ptr().add(idx));
                    let vc = _mm256_mul_ps(va, vs);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }

                if remainder > 0 {
                    let idx = chunks * 8;
                    let mut va_arr = [0.0f32; 8];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    let va = _mm256_loadu_ps(va_arr.as_ptr());
                    let vc = _mm256_mul_ps(va, vs);
                    let mut buf = [0.0f32; 8];
                    _mm256_storeu_ps(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        #[cfg(target_arch = "aarch64")]
        {
            let chunks = len / 4;
            let remainder = len % 4;
            unsafe {
                let vs = vdupq_n_f32(scalar);

                for i in 0..chunks {
                    let idx = i * 4;
                    let va = vld1q_f32(a.as_ptr().add(idx));
                    let vc = vmulq_f32(va, vs);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf);
                }

                if remainder > 0 {
                    let idx = chunks * 4;
                    let mut va_arr = [0.0f32; 4];
                    va_arr[..remainder].copy_from_slice(&a[idx..]);
                    let va = vld1q_f32(va_arr.as_ptr());
                    let vc = vmulq_f32(va, vs);
                    let mut buf = [0.0f32; 4];
                    vst1q_f32(buf.as_mut_ptr(), vc);
                    out.extend_from_slice(&buf[..remainder]);
                }
            }
        }

        out
    }
}

#[cfg(not(all(feature = "simd", any(target_arch = "x86_64", target_arch = "aarch64"))))]
pub mod simd_backend {
    /// Fallback scalar add when SIMD is not enabled or not supported.
    pub fn add(a: &[f32], b: &[f32]) -> Vec<f32> {
        a.iter().zip(b.iter()).map(|(&x, &y)| x + y).collect()
    }

    /// Fallback scalar mul when SIMD is not enabled or not supported.
    pub fn mul(a: &[f32], b: &[f32]) -> Vec<f32> {
        a.iter().zip(b.iter()).map(|(&x, &y)| x * y).collect()
    }

    /// Fallback scalar add_scalar when SIMD is not enabled or not supported.
    pub fn add_scalar(a: &[f32], scalar: f32) -> Vec<f32> {
        a.iter().map(|&x| x + scalar).collect()
    }

    /// Fallback scalar mul_scalar when SIMD is not enabled or not supported.
    pub fn mul_scalar(a: &[f32], scalar: f32) -> Vec<f32> {
        a.iter().map(|&x| x * scalar).collect()
    }
}

pub use simd_backend::{add, mul, add_scalar, mul_scalar};
