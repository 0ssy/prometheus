#include "usb.h"
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
#include <setupapi.h>
#include <initguid.h>
DEFINE_GUID(GUID_DEVINTERFACE_USB_DEVICE, 0xA5DCBF10L, 0x6530, 0x11D2, 0x90, 0x1F, 0x00, 0xC0, 0x4F, 0xB9, 0x51, 0xED);
#pragma comment(lib, "setupapi.lib")
#else
#include <libusb-1.0/libusb.h>
#endif

prom_usb_device_list_t prom_usb_enumerate(void) {
    prom_usb_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_USB_OK;

#ifdef _WIN32
    HDEVINFO dev_info = SetupDiGetClassDevsA(
        &GUID_DEVINTERFACE_USB_DEVICE,
        NULL,
        NULL,
        DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    );

    if (dev_info == INVALID_HANDLE_VALUE) {
        list.error = PROM_USB_ERR_INIT;
        return list;
    }

    SP_DEVICE_INTERFACE_DATA iface_data;
    iface_data.cbSize = sizeof(SP_DEVICE_INTERFACE_DATA);

    for (DWORD i = 0; i < PROM_USB_MAX_DEVICES; i++) {
        if (!SetupDiEnumDeviceInterfaces(dev_info, NULL, &GUID_DEVINTERFACE_USB_DEVICE, i, &iface_data)) {
            break;
        }

        SP_DEVINFO_DATA dev_data;
        dev_data.cbSize = sizeof(SP_DEVINFO_DATA);

        char desc[256];
        if (SetupDiGetDeviceRegistryPropertyA(dev_info, &dev_data, SPDRP_DEVICEDESC,
            NULL, (PBYTE)desc, sizeof(desc), NULL)) {
            snprintf(list.devices[list.count].product, sizeof(list.devices[list.count].product),
                "%s", desc);
            list.devices[list.count].vendor_id = 0x1234;
            list.devices[list.count].product_id = (uint16_t)i;
            list.count++;
        }
    }

    SetupDiDestroyDeviceInfoList(dev_info);
#else
    libusb_context *ctx = NULL;
    if (libusb_init(&ctx) != 0) {
        list.error = PROM_USB_ERR_INIT;
        return list;
    }

    libusb_device **devs;
    ssize_t cnt = libusb_get_device_list(ctx, &devs);
    if (cnt < 0) {
        list.error = PROM_USB_ERR_INIT;
        libusb_exit(ctx);
        return list;
    }

    for (ssize_t i = 0; i < cnt && list.count < PROM_USB_MAX_DEVICES; i++) {
        libusb_device *dev = devs[i];
        struct libusb_device_descriptor desc;
        if (libusb_get_device_descriptor(dev, &desc) != 0) continue;

        list.devices[list.count].vendor_id = desc.idVendor;
        list.devices[list.count].product_id = desc.idProduct;
        list.devices[list.count].bus_number = libusb_get_bus_number(dev);
        list.devices[list.count].device_address = libusb_get_device_address(dev);
        list.devices[list.count].class_code = desc.bDeviceClass;
        list.devices[list.count].subclass_code = desc.bDeviceSubClass;
        list.devices[list.count].protocol_code = desc.bDeviceProtocol;
        list.devices[list.count].max_packet_size = desc.bMaxPacketSize0;
        snprintf(list.devices[list.count].serial_number, sizeof(list.devices[list.count].serial_number),
            "usb-%d-%d", list.devices[list.count].bus_number, list.devices[list.count].device_address);
        list.count++;
    }

    libusb_free_device_list(devs, 1);
    libusb_exit(ctx);
#endif

    return list;
}

void prom_usb_free_device_list(prom_usb_device_list_t *list) {
    (void)list;
}

prom_usb_err_t prom_usb_probe(const char *target) {
    prom_usb_device_list_t list = prom_usb_enumerate();
    if (list.error != PROM_USB_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        char expected[128];
        snprintf(expected, sizeof(expected), "%04x:%04x",
            list.devices[i].vendor_id, list.devices[i].product_id);
        if (strncmp(target, expected, strlen(expected)) == 0) {
            return PROM_USB_OK;
        }
    }
    return PROM_USB_ERR_DEVICE_NOT_FOUND;
}

prom_usb_err_t prom_usb_open(uint16_t vendor_id, uint16_t product_id) {
    (void)vendor_id;
    (void)product_id;
    return PROM_USB_OK;
}

void prom_usb_close(void) {
}

prom_usb_transfer_result_t prom_usb_read(uint8_t endpoint, uint8_t *buffer, size_t length, uint32_t timeout_ms) {
    prom_usb_transfer_result_t result;
    memset(&result, 0, sizeof(result));
    (void)endpoint;
    (void)buffer;
    (void)length;
    (void)timeout_ms;
    result.error = PROM_USB_ERR_TRANSFER;
    return result;
}

prom_usb_transfer_result_t prom_usb_write(uint8_t endpoint, const uint8_t *buffer, size_t length, uint32_t timeout_ms) {
    prom_usb_transfer_result_t result;
    memset(&result, 0, sizeof(result));
    (void)endpoint;
    (void)buffer;
    (void)length;
    (void)timeout_ms;
    result.error = PROM_USB_ERR_TRANSFER;
    return result;
}

prom_usb_err_t prom_usb_get_descriptor(uint8_t type, uint8_t index, uint8_t *buffer, size_t length) {
    (void)type;
    (void)index;
    (void)buffer;
    (void)length;
    return PROM_USB_ERR_TRANSFER;
}

const char *prom_usb_strerror(prom_usb_err_t err) {
    switch (err) {
        case PROM_USB_OK: return "OK";
        case PROM_USB_ERR_NO_LIBUSB: return "libusb not available";
        case PROM_USB_ERR_INIT: return "initialization failed";
        case PROM_USB_ERR_DEVICE_NOT_FOUND: return "device not found";
        case PROM_USB_ERR_TRANSFER: return "transfer failed";
        case PROM_USB_ERR_TIMEOUT: return "timeout";
        case PROM_USB_ERR_MEMORY: return "out of memory";
        default: return "unknown error";
    }
}
