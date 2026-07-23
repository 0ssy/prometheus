#ifndef PROMETHEUS_HAL_HID_H
#define PROMETHEUS_HAL_HID_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_HID_MAX_DEVICES 128
#define PROM_HID_PATH_MAX 256

typedef enum {
    PROM_HID_OK = 0,
    PROM_HID_ERR_NO_HIDAPI = -1,
    PROM_HID_ERR_INIT = -2,
    PROM_HID_ERR_DEVICE_NOT_FOUND = -3,
    PROM_HID_ERR_TRANSFER = -4,
    PROM_HID_ERR_TIMEOUT = -5,
    PROM_HID_ERR_MEMORY = -6,
} prom_hid_err_t;

typedef struct {
    char path[PROM_HID_PATH_MAX];
    uint16_t vendor_id;
    uint16_t product_id;
    char manufacturer[64];
    char product[64];
    char serial_number[64];
    uint16_t usage_page;
    uint16_t usage_id;
    uint8_t interface_number;
} prom_hid_device_info_t;

typedef struct {
    prom_hid_device_info_t devices[PROM_HID_MAX_DEVICES];
    size_t count;
    prom_hid_err_t error;
} prom_hid_device_list_t;

prom_hid_device_list_t prom_hid_enumerate(void);
void prom_hid_free_device_list(prom_hid_device_list_t *list);
prom_hid_err_t prom_hid_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_HID_H */
