use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    if env::var_os("CARGO_FEATURE_CUDA").is_some() {
        let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
        let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
        let cuda_dir = manifest_dir.join("src/cuda");

        fs::create_dir_all(&out_dir).expect("failed to create out dir");

        let lib_name = if cfg!(target_os = "windows") { "tensor_cuda.lib" } else { "libtensor_cuda.a" };
        let lib_path = out_dir.join(lib_name);

        let mut cmd = Command::new("nvcc");
        if cfg!(target_os = "windows") {
            cmd.arg("-lib")
                .arg(cuda_dir.join("tensor_cuda.cu"))
                .arg("-o").arg(&lib_path)
                .arg("-std=c++14");
        } else {
            cmd.arg("-c")
                .arg(cuda_dir.join("tensor_cuda.cu"))
                .arg("-o").arg(out_dir.join("tensor_cuda.o"))
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
            let lib_path = out_dir.join("libtensor_cuda.a");
            let mut ar = Command::new("ar");
            ar.arg("rcs").arg(&lib_path).arg(out_dir.join("tensor_cuda.o"));

            let ar_status = ar.status().expect("failed to spawn ar");
            if !ar_status.success() {
                panic!("ar failed to create libtensor_cuda.a");
            }
            let _ = fs::remove_file(out_dir.join("tensor_cuda.o"));
        }

        println!("cargo:rustc-link-lib=static=tensor_cuda");
        println!("cargo:rustc-link-search=native={}", out_dir.display());
        if cfg!(target_os = "windows") {
            if let Ok(cuda_path) = env::var("CUDA_PATH") {
                println!("cargo:rustc-link-search=native={}\\lib\\x64", cuda_path);
            }
            println!("cargo:rustc-link-lib=cudart64_13");
        } else {
            println!("cargo:rustc-link-lib=cudart");
        }
        println!("cargo:rerun-if-changed={}", cuda_dir.join("tensor_cuda.cu").display());
    }
}
