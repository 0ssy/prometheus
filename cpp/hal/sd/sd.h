#ifndef PROMETHEUS_HAL_SD_H
#define PROMETHEUS_HAL_SD_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_SD_MAX_DEVICES 128
#define PROM_SD_PATH_MAX 256

typedef enum {
    PROM_SD_OK = 0,
    PROM_SD_ERR_INIT = -1,
    PROM_SD_ERR_DEVICE_NOT_FOUND = -2,
    PROM_SD_ERR_TRANSFER = -3,
    PROM_SD_ERR_TIMEOUT = -4,
    PROM_SD_ERR_MEMORY = -5,
} prom_sd_err_t;

typedef struct {
    char path[PROM_SD_PATH_MAX];
    uint64_t capacity_bytes;
    uint8_t speed_class;
    char manufacturer[64];
    char product[64];
} prom_sd_device_info_t;

typedef struct {
    prom_sd_device_info_t devices[PROM_SD_MAX_DEVICES];
    size_t count;
    prom_sd_err_t error;
} prom_sd_device_list_t;

prom_sd_device_list_t prom_sd_enumerate(void);
void prom_sd_free_device_list(prom_sd_device_list_t *list);
prom_sd_err_t prom_sd_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_SD_H */
