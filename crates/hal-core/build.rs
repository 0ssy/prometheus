use std::env;
use std::path::PathBuf;

fn main() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let cpp_dir = manifest_dir.parent().unwrap().parent().unwrap().join("cpp");

    let mut build = cc::Build::new();
    build.cpp(true);
    build.include(&cpp_dir);
    build.include(cpp_dir.join("hal"));
    build.include(cpp_dir.join("hal/usb"));
    build.include(cpp_dir.join("hal/serial"));
    build.include(cpp_dir.join("hal/gpio"));

    build.file(cpp_dir.join("hal/usb/usb.c"));
    build.file(cpp_dir.join("hal/serial/serial.c"));
    build.file(cpp_dir.join("hal/gpio/gpio.c"));

    if cfg!(target_os = "windows") {
        println!("cargo:rustc-link-lib=setupapi");
    } else if cfg!(target_os = "linux") {
        if let Ok(lib_dir) = env::var("LIBUSB_1_0_LIBRARY_DIRS") {
            println!("cargo:rustc-link-search=native={}", lib_dir);
        }
        if let Ok(lib_dir) = env::var("LIBSERIALPORT_LIBRARY_DIRS") {
            println!("cargo:rustc-link-search=native={}", lib_dir);
        }
        println!("cargo:rustc-link-lib=usb-1.0");
        println!("cargo:rustc-link-lib=serialport");
    } else if cfg!(target_os = "macos") {
        println!("cargo:rustc-link-lib=framework=IOKit");
        println!("cargo:rustc-link-lib=framework=CoreFoundation");
    }

    build.compile("prom_hal_core");

    let bindings = bindgen::Builder::default()
        .header(cpp_dir.join("hal/usb/usb.h").to_str().unwrap())
        .header(cpp_dir.join("hal/serial/serial.h").to_str().unwrap())
        .header(cpp_dir.join("hal/gpio/gpio.h").to_str().unwrap())
        .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
        .generate()
        .expect("Unable to generate bindings");

    bindings
        .write_to_file(out_dir.join("hal_bindings.rs"))
        .expect("Couldn't write bindings!");

    println!("cargo:rerun-if-changed={}", cpp_dir.join("hal/usb/usb.c").display());
    println!("cargo:rerun-if-changed={}", cpp_dir.join("hal/usb/usb.h").display());
    println!("cargo:rerun-if-changed={}", cpp_dir.join("hal/serial/serial.c").display());
    println!("cargo:rerun-if-changed={}", cpp_dir.join("hal/serial/serial.h").display());
    println!("cargo:rerun-if-changed={}", cpp_dir.join("hal/gpio/gpio.c").display());
    println!("cargo:rerun-if-changed={}", cpp_dir.join("hal/gpio/gpio.h").display());
}
