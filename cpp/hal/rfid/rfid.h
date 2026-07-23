#ifndef PROMETHEUS_HAL_RFID_H
#define PROMETHEUS_HAL_RFID_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_RFID_MAX_DEVICES 128
#define PROM_RFID_PATH_MAX 256

typedef enum {
    PROM_RFID_OK = 0,
    PROM_RFID_ERR_INIT = -1,
    PROM_RFID_ERR_DEVICE_NOT_FOUND = -2,
    PROM_RFID_ERR_TRANSFER = -3,
    PROM_RFID_ERR_TIMEOUT = -4,
    PROM_RFID_ERR_MEMORY = -5,
} prom_rfid_err_t;

typedef enum {
    PROM_RFID_FREQ_125KHZ = 0,
    PROM_RFID_FREQ_13_56MHZ,
} prom_rfid_freq_t;

typedef struct {
    char path[PROM_RFID_PATH_MAX];
    uint16_t vendor_id;
    uint16_t product_id;
    prom_rfid_freq_t frequency;
    char manufacturer[64];
    char product[64];
} prom_rfid_device_info_t;

typedef struct {
    prom_rfid_device_info_t devices[PROM_RFID_MAX_DEVICES];
    size_t count;
    prom_rfid_err_t error;
} prom_rfid_device_list_t;

prom_rfid_device_list_t prom_rfid_enumerate(void);
void prom_rfid_free_device_list(prom_rfid_device_list_t *list);
prom_rfid_err_t prom_rfid_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_RFID_H */
