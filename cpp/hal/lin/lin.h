#ifndef PROMETHEUS_HAL_LIN_H
#define PROMETHEUS_HAL_LIN_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_LIN_MAX_DEVICES 128
#define PROM_LIN_PATH_MAX 256

typedef enum {
    PROM_LIN_OK = 0,
    PROM_LIN_ERR_INIT = -1,
    PROM_LIN_ERR_DEVICE_NOT_FOUND = -2,
    PROM_LIN_ERR_TRANSFER = -3,
    PROM_LIN_ERR_TIMEOUT = -4,
    PROM_LIN_ERR_MEMORY = -5,
} prom_lin_err_t;

typedef struct {
    char interface[PROM_LIN_PATH_MAX];
    uint16_t vendor_id;
    uint16_t product_id;
    uint32_t baud_rate;
    char manufacturer[64];
    char product[64];
} prom_lin_device_info_t;

typedef struct {
    prom_lin_device_info_t devices[PROM_LIN_MAX_DEVICES];
    size_t count;
    prom_lin_err_t error;
} prom_lin_device_list_t;

prom_lin_device_list_t prom_lin_enumerate(void);
void prom_lin_free_device_list(prom_lin_device_list_t *list);
prom_lin_err_t prom_lin_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_LIN_H */
