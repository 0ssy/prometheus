#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <math.h>
#include <stdio.h>

#define CHECK(call)                                                     \
    do {                                                                \
        cudaError_t err = call;                                         \
        if (err != cudaSuccess) {                                       \
            fprintf(stderr, "CUDA error in %s (%s:%d): %s\n",           \
                    __func__, __FILE__, __LINE__, cudaGetErrorString(err)); \
            return err;                                                 \
        }                                                               \
    } while (0)

__global__ void add_kernel(const float *a, const float *b, float *out, size_t n) {
    size_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) out[i] = a[i] + b[i];
}

__global__ void matmul_kernel(const float *a, const float *b, float *c, int M, int K, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    if (row < M && col < N) {
        float sum = 0.0f;
        for (int k = 0; k < K; k++) {
            sum += a[row * K + k] * b[k * N + col];
        }
        c[row * N + col] = sum;
    }
}

__global__ void softmax_kernel(float *x, int rows, int cols) {
    __shared__ float smax[1024];
    int r = blockIdx.x;
    int tid = threadIdx.x;
    if (tid < cols) {
        float v = x[r * cols + tid];
        smax[tid] = v;
    }
    __syncthreads();
    if (tid == 0) {
        float mx = -INFINITY;
        for (int i = 0; i < cols; i++) mx = fmaxf(mx, smax[i]);
        float s = 0.0f;
        for (int i = 0; i < cols; i++) {
            smax[i] = __expf(smax[i] - mx);
            s += smax[i];
        }
        for (int i = 0; i < cols; i++) {
            x[r * cols + i] = s > 0.0f ? smax[i] / s : 0.0f;
        }
    }
}

extern "C" {

cudaError_t cuda_tensor_add(const float *h_a, const float *h_b, float *h_out, size_t n) {
    float *d_a, *d_b, *d_out;
    CHECK(cudaMalloc((void**)&d_a, n * sizeof(float)));
    CHECK(cudaMalloc((void**)&d_b, n * sizeof(float)));
    CHECK(cudaMalloc((void**)&d_out, n * sizeof(float)));
    CHECK(cudaMemcpy(d_a, h_a, n * sizeof(float), cudaMemcpyHostToDevice));
    CHECK(cudaMemcpy(d_b, h_b, n * sizeof(float), cudaMemcpyHostToDevice));
    int threads = 256;
    int blocks = (n + threads - 1) / threads;
    add_kernel<<<blocks, threads>>>(d_a, d_b, d_out, n);
    CHECK(cudaDeviceSynchronize());
    CHECK(cudaMemcpy(h_out, d_out, n * sizeof(float), cudaMemcpyDeviceToHost));
    cudaFree(d_a); cudaFree(d_b); cudaFree(d_out);
    return cudaSuccess;
}

cudaError_t cuda_matmul(const float *h_a, const float *h_b, float *h_c, int M, int K, int N) {
    float *d_a, *d_b, *d_c;
    CHECK(cudaMalloc((void**)&d_a, M * K * sizeof(float)));
    CHECK(cudaMalloc((void**)&d_b, K * N * sizeof(float)));
    CHECK(cudaMalloc((void**)&d_c, M * N * sizeof(float)));
    CHECK(cudaMemcpy(d_a, h_a, M * K * sizeof(float), cudaMemcpyHostToDevice));
    CHECK(cudaMemcpy(d_b, h_b, K * N * sizeof(float), cudaMemcpyHostToDevice));
    dim3 threads(16, 16);
    dim3 blocks((N + 15) / 16, (M + 15) / 16);
    matmul_kernel<<<blocks, threads>>>(d_a, d_b, d_c, M, K, N);
    CHECK(cudaDeviceSynchronize());
    CHECK(cudaMemcpy(h_c, d_c, M * N * sizeof(float), cudaMemcpyDeviceToHost));
    cudaFree(d_a); cudaFree(d_b); cudaFree(d_c);
    return cudaSuccess;
}

cudaError_t cuda_softmax(float *h_x, int rows, int cols) {
    float *d_x;
    CHECK(cudaMalloc((void**)&d_x, rows * cols * sizeof(float)));
    CHECK(cudaMemcpy(d_x, h_x, rows * cols * sizeof(float), cudaMemcpyHostToDevice));
    softmax_kernel<<<rows, cols>>>(d_x, rows, cols);
    CHECK(cudaDeviceSynchronize());
    CHECK(cudaMemcpy(h_x, d_x, rows * cols * sizeof(float), cudaMemcpyDeviceToHost));
    cudaFree(d_x);
    return cudaSuccess;
}

}
