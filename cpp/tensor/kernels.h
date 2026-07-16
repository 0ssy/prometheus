// P6 High Performance Engine — tensor compute kernels (C).
//
// Wrapped into Rust `tensor-engine` via `cc`/`bindgen` and (on GPU) into
// the CUDA runtime. This is the portable CPU reference kernel; the
// production path uses optimized/SIMD/CUDA variants.
#ifndef PROMETHEUS_TENSOR_KERNELS_H
#define PROMETHEUS_TENSOR_KERNELS_H

#ifdef __cplusplus
extern "C" {
#endif

// out[m*n] = a[m*k] * b[k*n] (row-major). Returns 0 on success.
int prometheus_matmul(const float* a, const float* b, float* out,
                      int m, int k, int n);

// out[i] = a[i] + b[i] for i in [0, n).
int prometheus_add(const float* a, const float* b, float* out, int n);

#ifdef __cplusplus
}
#endif

#endif // PROMETHEUS_TENSOR_KERNELS_H
