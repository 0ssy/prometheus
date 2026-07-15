# P9 Prometheus SDK — C++ header-only SDK build.
#
# CMake config for downstream C++ extensions (the plan's P9 C++ SDK).
# The native kernels (cpp/tensor, cpp/hardware) are compiled into the
# Rust crates via `cc`/`bindgen`; this target is for external C++ consumers.

cmake_minimum_required(VERSION 3.16)
project(prometheus_sdk C CXX)

add_library(prometheus_tensor STATIC cpp/tensor/kernels.c)
add_library(prometheus_usb STATIC cpp/hardware/drivers/usb.c)

target_include_directories(prometheus_tensor PUBLIC cpp/tensor)
target_include_directories(prometheus_usb PUBLIC cpp/hardware/drivers)

install(TARGETS prometheus_tensor prometheus_usb)
