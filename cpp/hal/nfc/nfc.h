#ifndef PROMETHEUS_HAL_NFC_H
#define PROMETHEUS_HAL_NFC_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_NFC_MAX_DEVICES 128
#define PROM_NFC_PATH_MAX 256

typedef enum {
    PROM_NFC_OK = 0,
    PROM_NFC_ERR_INIT = -1,
    PROM_NFC_ERR_DEVICE_NOT_FOUND = -2,
    PROM_NFC_ERR_TRANSFER = -3,
    PROM_NFC_ERR_TIMEOUT = -4,
    PROM_NFC_ERR_MEMORY = -5,
} prom_nfc_err_t;

typedef struct {
    char path[PROM_NFC_PATH_MAX];
    uint16_t vendor_id;
    uint16_t product_id;
    bool supports_nfc_a;
    bool supports_nfc_b;
    bool supports_nfc_v;
    char manufacturer[64];
    char product[64];
} prom_nfc_device_info_t;

typedef struct {
    prom_nfc_device_info_t devices[PROM_NFC_MAX_DEVICES];
    size_t count;
    prom_nfc_err_t error;
} prom_nfc_device_list_t;

prom_nfc_device_list_t prom_nfc_enumerate(void);
void prom_nfc_free_device_list(prom_nfc_device_list_t *list);
prom_nfc_err_t prom_nfc_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_NFC_H */
