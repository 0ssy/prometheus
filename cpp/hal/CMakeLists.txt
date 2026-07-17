cmake_minimum_required(VERSION 3.16)
project(prometheus_hal C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

option(BUILD_HAL_USB "Build USB HAL transport" ON)
option(BUILD_HAL_SERIAL "Build Serial HAL transport" ON)
option(BUILD_HAL_GPIO "Build GPIO HAL transport" ON)
option(BUILD_HAL_SPI "Build SPI HAL transport" OFF)
option(BUILD_HAL_I2C "Build I2C HAL transport" OFF)
option(BUILD_HAL_CAN "Build CAN HAL transport" OFF)
option(BUILD_HAL_JTAG "Build JTAG HAL transport" OFF)

if(WIN32)
    find_library(WINUSB_LIBRARY winusb)
    find_library(SETUPAPI_LIBRARY setupapi)
endif()

if(UNIX AND NOT APPLE)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(LIBUSB REQUIRED libusb-1.0)
    pkg_check_modules(LIBSERIALPORT REQUIRED libserialport)
endif()

add_library(prom_hal_core INTERFACE)
target_include_directories(prom_hal_core INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/..
)

if(BUILD_HAL_USB)
    add_library(prom_hal_usb STATIC usb/usb.c)
    target_include_directories(prom_hal_usb PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/usb)
    if(WIN32)
        target_link_libraries(prom_hal_usb PRIVATE setupapi)
    elseif(UNIX AND NOT APPLE)
        target_include_directories(prom_hal_usb PRIVATE ${LIBUSB_INCLUDE_DIRS})
        target_link_libraries(prom_hal_usb PRIVATE ${LIBUSB_LIBRARIES})
        target_compile_definitions(prom_hal_usb PRIVATE HAVE_LIBUSB)
    endif()
    target_link_libraries(prom_hal_core INTERFACE prom_hal_usb)
endif()

if(BUILD_HAL_SERIAL)
    add_library(prom_hal_serial STATIC serial/serial.c)
    target_include_directories(prom_hal_serial PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/serial)
    if(UNIX AND NOT APPLE AND LIBSERIALPORT_FOUND)
        target_include_directories(prom_hal_serial PRIVATE ${LIBSERIALPORT_INCLUDE_DIRS})
        target_link_libraries(prom_hal_serial PRIVATE ${LIBSERIALPORT_LIBRARIES})
        target_compile_definitions(prom_hal_serial PRIVATE HAVE_LIBSERIALPORT)
    endif()
    target_link_libraries(prom_hal_core INTERFACE prom_hal_serial)
endif()

if(BUILD_HAL_GPIO)
    add_library(prom_hal_gpio STATIC gpio/gpio.c)
    target_include_directories(prom_hal_gpio PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/gpio)
    target_link_libraries(prom_hal_core INTERFACE prom_hal_gpio)
endif()

install(TARGETS prom_hal_core
    EXPORT prometheus_hal_targets
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)

if(BUILD_HAL_USB)
    install(TARGETS prom_hal_usb
        EXPORT prometheus_hal_targets
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
    )
    install(FILES usb/usb.h DESTINATION include/prometheus/hal)
endif()

if(BUILD_HAL_SERIAL)
    install(TARGETS prom_hal_serial
        EXPORT prometheus_hal_targets
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
    )
    install(FILES serial/serial.h DESTINATION include/prometheus/hal)
endif()

if(BUILD_HAL_GPIO)
    install(TARGETS prom_hal_gpio
        EXPORT prometheus_hal_targets
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
    )
    install(FILES gpio/gpio.h DESTINATION include/prometheus/hal)
endif()
