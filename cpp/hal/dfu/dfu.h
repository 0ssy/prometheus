#ifndef PROMETHEUS_HAL_DFU_H
#define PROMETHEUS_HAL_DFU_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_DFU_MAX_DEVICES 128
#define PROM_DFU_PATH_MAX 256

typedef enum {
    PROM_DFU_OK = 0,
    PROM_DFU_ERR_UTIL = -1,
    PROM_DFU_ERR_INIT = -2,
    PROM_DFU_ERR_DEVICE_NOT_FOUND = -3,
    PROM_DFU_ERR_TRANSFER = -4,
    PROM_DFU_ERR_TIMEOUT = -5,
    PROM_DFU_ERR_MEMORY = -6,
} prom_dfu_err_t;

typedef struct {
    char path[PROM_DFU_PATH_MAX];
    uint16_t vendor_id;
    uint16_t product_id;
    char state[32];
    uint16_t firmware_version;
    bool can_detach;
} prom_dfu_device_info_t;

typedef struct {
    prom_dfu_device_info_t devices[PROM_DFU_MAX_DEVICES];
    size_t count;
    prom_dfu_err_t error;
} prom_dfu_device_list_t;

prom_dfu_device_list_t prom_dfu_enumerate(void);
void prom_dfu_free_device_list(prom_dfu_device_list_t *list);
prom_dfu_err_t prom_dfu_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_DFU_H */
