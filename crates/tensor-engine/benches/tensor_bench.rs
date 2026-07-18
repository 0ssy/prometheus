use criterion::{black_box, criterion_group, criterion_main, Criterion};
use tensor_engine::Tensor;

pub fn matmul_256(c: &mut Criterion) {
    let size = 256;
    let a_data: Vec<f32> = (0..size * size).map(|i| (i % 97) as f32).collect();
    let b_data: Vec<f32> = (0..size * size).map(|i| (i % 53) as f32).collect();
    let a = Tensor::new(vec![size, size], a_data);
    let b = Tensor::new(vec![size, size], b_data);
    c.bench_function("matmul 256x256", |bench| {
        bench.iter(|| black_box(a.matmul(black_box(&b))))
    });
}

pub fn add_4096(c: &mut Criterion) {
    let size = 4096;
    let a_data: Vec<f32> = (0..size).map(|i| (i % 97) as f32).collect();
    let b_data: Vec<f32> = (0..size).map(|i| (i % 53) as f32).collect();
    let a = Tensor::new(vec![size], a_data);
    let b = Tensor::new(vec![size], b_data);
    c.bench_function("add 4096", |bench| {
        bench.iter(|| black_box(a.add(black_box(&b))))
    });
}

pub fn softmax_4096(c: &mut Criterion) {
    let size = 4096;
    let data: Vec<f32> = (0..size).map(|i| (i % 97) as f32).collect();
    let t = Tensor::new(vec![size], data);
    c.bench_function("softmax 4096", |bench| {
        bench.iter(|| black_box(t.softmax()))
    });
}

pub fn layer_norm_4096(c: &mut Criterion) {
    let size = 4096;
    let data: Vec<f32> = (0..size).map(|i| (i % 97) as f32).collect();
    let t = Tensor::new(vec![size], data);
    c.bench_function("layer_norm 4096", |bench| {
        bench.iter(|| black_box(t.layer_norm(black_box(1e-5))))
    });
}

criterion_group!(benches, matmul_256, add_4096, softmax_4096, layer_norm_4096);
criterion_main!(benches);
