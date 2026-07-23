#ifndef PROMETHEUS_HAL_SWD_H
#define PROMETHEUS_HAL_SWD_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_SWD_MAX_DEVICES 128
#define PROM_SWD_ID_MAX 64

typedef enum {
    PROM_SWD_OK = 0,
    PROM_SWD_ERR_OPENOCD = -1,
    PROM_SWD_ERR_INIT = -2,
    PROM_SWD_ERR_DEVICE_NOT_FOUND = -3,
    PROM_SWD_ERR_TRANSFER = -4,
    PROM_SWD_ERR_TIMEOUT = -5,
    PROM_SWD_ERR_MEMORY = -6,
} prom_swd_err_t;

typedef struct {
    char target_id[PROM_SWD_ID_MAX];
    uint32_t idcode;
    char core[32];
    uint8_t dp_version;
    uint32_t serial;
} prom_swd_device_info_t;

typedef struct {
    prom_swd_device_info_t devices[PROM_SWD_MAX_DEVICES];
    size_t count;
    prom_swd_err_t error;
} prom_swd_device_list_t;

prom_swd_device_list_t prom_swd_enumerate(void);
void prom_swd_free_device_list(prom_swd_device_list_t *list);
prom_swd_err_t prom_swd_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_SWD_H */
