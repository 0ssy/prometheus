#ifndef PROMETHEUS_HAL_SATA_H
#define PROMETHEUS_HAL_SATA_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_SATA_MAX_DEVICES 128
#define PROM_SATA_MODEL_MAX 40
#define PROM_SATA_SERIAL_MAX 20
#define PROM_SATA_FW_MAX 8

typedef enum {
    PROM_SATA_OK = 0,
    PROM_SATA_ERR_INIT = -1,
    PROM_SATA_ERR_DEVICE_NOT_FOUND = -2,
    PROM_SATA_ERR_TRANSFER = -3,
    PROM_SATA_ERR_TIMEOUT = -4,
    PROM_SATA_ERR_MEMORY = -5,
} prom_sata_err_t;

typedef struct {
    char port[16];
    char model[PROM_SATA_MODEL_MAX];
    char serial[PROM_SATA_SERIAL_MAX];
    char firmware_version[PROM_SATA_FW_MAX];
    uint64_t capacity_bytes;
} prom_sata_device_info_t;

typedef struct {
    prom_sata_device_info_t devices[PROM_SATA_MAX_DEVICES];
    size_t count;
    prom_sata_err_t error;
} prom_sata_device_list_t;

prom_sata_device_list_t prom_sata_enumerate(void);
void prom_sata_free_device_list(prom_sata_device_list_t *list);
prom_sata_err_t prom_sata_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_SATA_H */
