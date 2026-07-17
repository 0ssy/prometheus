use std::env;
use std::path::PathBuf;
use std::process::Command;

fn nvcc_available() -> bool {
    env::var_os("CUDA_PATH").is_some()
        || Command::new("nvcc").arg("--version").output().map(|o| o.status.success()).unwrap_or(false)
}

fn main() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let cuda_dir = manifest_dir.join("src/cuda");

    if env::var_os("CARGO_FEATURE_CUDA").is_some() {
        if nvcc_available() {
            let mut build = cc::Build::new();
            build.cpp(true);
            build.include(&cuda_dir);
            build.file(cuda_dir.join("tensor_cuda.cu"));
            build.flag("-std=c++14");
            build.compile("tensor_cuda");
            println!("cargo:rustc-link-lib=static=tensor_cuda");
            println!("cargo:rustc-link-search=native={}", out_dir.display());
        } else {
            println!("cargo:warning=nvcc not found; CUDA kernels will not be compiled");
        }
    }
}
