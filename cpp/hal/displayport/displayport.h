#ifndef PROMETHEUS_HAL_DISPLAYPORT_H
#define PROMETHEUS_HAL_DISPLAYPORT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_DP_MAX_DEVICES 128
#define PROM_DP_PATH_MAX 256

typedef enum {
    PROM_DP_OK = 0,
    PROM_DP_ERR_INIT = -1,
    PROM_DP_ERR_DEVICE_NOT_FOUND = -2,
    PROM_DP_ERR_TRANSFER = -3,
    PROM_DP_ERR_TIMEOUT = -4,
    PROM_DP_ERR_MEMORY = -5,
} prom_dp_err_t;

typedef struct {
    char path[PROM_DP_PATH_MAX];
    uint16_t width;
    uint16_t height;
    uint32_t refresh_rate_hz;
    char manufacturer[64];
    char product[64];
} prom_dp_device_info_t;

typedef struct {
    prom_dp_device_info_t devices[PROM_DP_MAX_DEVICES];
    size_t count;
    prom_dp_err_t error;
} prom_dp_device_list_t;

prom_dp_device_list_t prom_dp_enumerate(void);
void prom_dp_free_device_list(prom_dp_device_list_t *list);
prom_dp_err_t prom_dp_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_DISPLAYPORT_H */
