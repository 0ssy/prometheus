struct Params {
    M: u32,
    K: u32,
    N: u32,
}

@group(0) @binding(0) var<storage, read> a: array<f32>;
@group(0) @binding(1) var<storage, read> b: array<f32>;
@group(0) @binding(2) var<storage, read_write> c: array<f32>;
@group(0) @binding(3) var<uniform> params: Params;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    if (idx >= params.M * params.N) {
        return;
    }
    let row = idx / params.N;
    let col = idx % params.N;
    var sum = 0.0;
    for (var k = 0u; k < params.K; k = k + 1u) {
        sum = sum + a[row * params.K + k] * b[k * params.N + col];
    }
    c[idx] = sum;
}
