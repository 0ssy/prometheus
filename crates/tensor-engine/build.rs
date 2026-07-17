use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let cuda_dir = manifest_dir.join("src/cuda");

    let cuda_enabled = env::var_os("CARGO_FEATURE_CUDA").is_some();
    eprintln!("tensor-engine build.rs: CARGO_FEATURE_CUDA={:?}", env::var_os("CARGO_FEATURE_CUDA"));
    eprintln!("tensor-engine build.rs: cuda_enabled={}", cuda_enabled);

    if cuda_enabled {
        let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
        let workspace_target = manifest_dir.parent().unwrap().parent().unwrap().join("target");
        let profile = env::var("PROFILE").unwrap_or_else(|_| "debug".to_string());
        let cuda_out = workspace_target.join(&profile).join("cuda_objs");
        fs::create_dir_all(&cuda_out).expect("failed to create cuda out dir");

        let lib_name = if cfg!(target_os = "windows") { "tensor_cuda.lib" } else { "libtensor_cuda.a" };
        let lib_path = cuda_out.join(lib_name);

        let mut cmd = Command::new("nvcc");
        if cfg!(target_os = "windows") {
            cmd.arg("-lib")
                .arg(cuda_dir.join("tensor_cuda.cu"))
                .arg("-o").arg(&lib_path)
                .arg("-std=c++14");
        } else {
            cmd.arg("-c")
                .arg(cuda_dir.join("tensor_cuda.cu"))
                .arg("-o").arg(cuda_out.join("tensor_cuda.o"))
                .arg("-std=c++14");
        }

        if let Ok(host) = env::var("CUDAHOSTCXX") {
            cmd.arg("-ccbin").arg(host);
        }

        let status = cmd.status().expect("failed to spawn nvcc");
        if !status.success() {
            panic!("nvcc failed to compile tensor_cuda.cu");
        }

        if !cfg!(target_os = "windows") {
            let lib_path = cuda_out.join("libtensor_cuda.a");
            let mut ar = Command::new("ar");
            ar.arg("rcs").arg(&lib_path).arg(cuda_out.join("tensor_cuda.o"));

            let ar_status = ar.status().expect("failed to spawn ar");
            if !ar_status.success() {
                panic!("ar failed to create libtensor_cuda.a");
            }
            let _ = fs::remove_file(cuda_out.join("tensor_cuda.o"));
        }

        println!("cargo:rustc-link-lib=static=tensor_cuda");
        println!("cargo:rustc-link-search=native={}", cuda_out.display());
        if cfg!(target_os = "windows") {
            if let Ok(cuda_path) = env::var("CUDA_PATH") {
                println!("cargo:rustc-link-search=native={}\\lib\\x64", cuda_path);
            }
            println!("cargo:rustc-link-lib=cuda");
            println!("cargo:rustc-link-lib=cudadevrt");
        } else {
            println!("cargo:rustc-link-lib=cudart");
        }
        println!("cargo:rerun-if-changed={}", cuda_dir.join("tensor_cuda.cu").display());
    }
}
