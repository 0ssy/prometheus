cmake_minimum_required(VERSION 3.16)
project(prometheus_sdk C CXX)

add_subdirectory(hal)

add_library(prometheus_tensor STATIC tensor/kernels.c)
add_library(prometheus_usb STATIC hardware/drivers/usb.c)

target_include_directories(prometheus_tensor PUBLIC tensor)
target_include_directories(prometheus_usb PUBLIC hardware/drivers)
target_link_libraries(prometheus_usb PRIVATE prom_hal_core)

install(TARGETS prometheus_tensor prometheus_usb)
