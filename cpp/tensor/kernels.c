// P6 High Performance Engine — tensor compute kernels implementation (C).
#include "kernels.h"
#include <stddef.h>

int prometheus_matmul(const float* a, const float* b, float* out,
                      int m, int k, int n) {
    if (m <= 0 || k <= 0 || n <= 0) return -1;
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < n; ++j) {
            float acc = 0.0f;
            for (int p = 0; p < k; ++p) {
                acc += a[(size_t)i * k + p] * b[(size_t)p * n + j];
            }
            out[(size_t)i * n + j] = acc;
        }
    }
    return 0;
}

int prometheus_add(const float* a, const float* b, float* out, int n) {
    if (n <= 0) return -1;
    for (int i = 0; i < n; ++i) out[i] = a[i] + b[i];
    return 0;
}
