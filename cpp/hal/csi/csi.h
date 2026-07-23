#ifndef PROMETHEUS_HAL_CSI_H
#define PROMETHEUS_HAL_CSI_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_CSI_MAX_DEVICES 128
#define PROM_CSI_PATH_MAX 256

typedef enum {
    PROM_CSI_OK = 0,
    PROM_CSI_ERR_INIT = -1,
    PROM_CSI_ERR_DEVICE_NOT_FOUND = -2,
    PROM_CSI_ERR_TRANSFER = -3,
    PROM_CSI_ERR_TIMEOUT = -4,
    PROM_CSI_ERR_MEMORY = -5,
} prom_csi_err_t;

typedef struct {
    char path[PROM_CSI_PATH_MAX];
    uint16_t lanes;
    uint32_t refresh_rate_hz;
    char manufacturer[64];
    char product[64];
} prom_csi_device_info_t;

typedef struct {
    prom_csi_device_info_t devices[PROM_CSI_MAX_DEVICES];
    size_t count;
    prom_csi_err_t error;
} prom_csi_device_list_t;

prom_csi_device_list_t prom_csi_enumerate(void);
void prom_csi_free_device_list(prom_csi_device_list_t *list);
prom_csi_err_t prom_csi_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_CSI_H */
