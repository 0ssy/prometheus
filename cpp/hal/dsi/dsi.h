#ifndef PROMETHEUS_HAL_DSI_H
#define PROMETHEUS_HAL_DSI_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_DSI_MAX_DEVICES 128
#define PROM_DSI_PATH_MAX 256

typedef enum {
    PROM_DSI_OK = 0,
    PROM_DSI_ERR_INIT = -1,
    PROM_DSI_ERR_DEVICE_NOT_FOUND = -2,
    PROM_DSI_ERR_TRANSFER = -3,
    PROM_DSI_ERR_TIMEOUT = -4,
    PROM_DSI_ERR_MEMORY = -5,
} prom_dsi_err_t;

typedef struct {
    char path[PROM_DSI_PATH_MAX];
    uint16_t lanes;
    uint32_t refresh_rate_hz;
    char manufacturer[64];
    char product[64];
} prom_dsi_device_info_t;

typedef struct {
    prom_dsi_device_info_t devices[PROM_DSI_MAX_DEVICES];
    size_t count;
    prom_dsi_err_t error;
} prom_dsi_device_list_t;

prom_dsi_device_list_t prom_dsi_enumerate(void);
void prom_dsi_free_device_list(prom_dsi_device_list_t *list);
prom_dsi_err_t prom_dsi_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_DSI_H */
