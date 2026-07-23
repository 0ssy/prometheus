#ifndef PROMETHEUS_HAL_MIPI_H
#define PROMETHEUS_HAL_MIPI_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_MIPI_MAX_DEVICES 128
#define PROM_MIPI_PATH_MAX 256

typedef enum {
    PROM_MIPI_OK = 0,
    PROM_MIPI_ERR_INIT = -1,
    PROM_MIPI_ERR_DEVICE_NOT_FOUND = -2,
    PROM_MIPI_ERR_TRANSFER = -3,
    PROM_MIPI_ERR_TIMEOUT = -4,
    PROM_MIPI_ERR_MEMORY = -5,
} prom_mipi_err_t;

typedef struct {
    char path[PROM_MIPI_PATH_MAX];
    uint16_t lanes;
    uint32_t refresh_rate_hz;
    char manufacturer[64];
    char product[64];
} prom_mipi_device_info_t;

typedef struct {
    prom_mipi_device_info_t devices[PROM_MIPI_MAX_DEVICES];
    size_t count;
    prom_mipi_err_t error;
} prom_mipi_device_list_t;

prom_mipi_device_list_t prom_mipi_enumerate(void);
void prom_mipi_free_device_list(prom_mipi_device_list_t *list);
prom_mipi_err_t prom_mipi_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_MIPI_H */
