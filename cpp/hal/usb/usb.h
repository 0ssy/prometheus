#ifndef PROMETHEUS_HAL_USB_H
#define PROMETHEUS_HAL_USB_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_USB_MAX_DESCRIPTOR 256
#define PROM_USB_MAX_DEVICES 128

typedef enum {
    PROM_USB_OK = 0,
    PROM_USB_ERR_NO_LIBUSB = -1,
    PROM_USB_ERR_INIT = -2,
    PROM_USB_ERR_DEVICE_NOT_FOUND = -3,
    PROM_USB_ERR_TRANSFER = -4,
    PROM_USB_ERR_TIMEOUT = -5,
    PROM_USB_ERR_MEMORY = -6,
} prom_usb_err_t;

typedef struct {
    uint16_t vendor_id;
    uint16_t product_id;
    uint8_t bus_number;
    uint8_t device_address;
    char serial_number[64];
    char manufacturer[64];
    char product[64];
    uint8_t class_code;
    uint8_t subclass_code;
    uint8_t protocol_code;
    uint16_t max_packet_size;
} prom_usb_device_info_t;

typedef struct {
    prom_usb_device_info_t devices[PROM_USB_MAX_DEVICES];
    size_t count;
    prom_usb_err_t error;
} prom_usb_device_list_t;

typedef struct {
    uint8_t *buffer;
    size_t length;
    size_t transferred;
    prom_usb_err_t error;
} prom_usb_transfer_result_t;

prom_usb_device_list_t prom_usb_enumerate(void);
void prom_usb_free_device_list(prom_usb_device_list_t *list);
prom_usb_err_t prom_usb_probe(const char *target);
prom_usb_err_t prom_usb_open(uint16_t vendor_id, uint16_t product_id);
void prom_usb_close(void);
prom_usb_transfer_result_t prom_usb_read(uint8_t endpoint, uint8_t *buffer, size_t length, uint32_t timeout_ms);
prom_usb_transfer_result_t prom_usb_write(uint8_t endpoint, const uint8_t *buffer, size_t length, uint32_t timeout_ms);
prom_usb_err_t prom_usb_get_descriptor(uint8_t type, uint8_t index, uint8_t *buffer, size_t length);
const char *prom_usb_strerror(prom_usb_err_t err);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_USB_H */
