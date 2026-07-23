#ifndef PROMETHEUS_HAL_BACNET_H
#define PROMETHEUS_HAL_BACNET_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_BACNET_MAX_DEVICES 128
#define PROM_BACNET_IP_MAX 64

typedef enum {
    PROM_BACNET_OK = 0,
    PROM_BACNET_ERR_INIT = -1,
    PROM_BACNET_ERR_DEVICE_NOT_FOUND = -2,
    PROM_BACNET_ERR_TRANSFER = -3,
    PROM_BACNET_ERR_TIMEOUT = -4,
    PROM_BACNET_ERR_MEMORY = -5,
} prom_bacnet_err_t;

typedef struct {
    uint32_t device_id;
    char ip_address[PROM_BACNET_IP_MAX];
    uint16_t vendor_id;
    size_t object_count;
} prom_bacnet_device_info_t;

typedef struct {
    prom_bacnet_device_info_t devices[PROM_BACNET_MAX_DEVICES];
    size_t count;
    prom_bacnet_err_t error;
} prom_bacnet_device_list_t;

prom_bacnet_device_list_t prom_bacnet_enumerate(void);
void prom_bacnet_free_device_list(prom_bacnet_device_list_t *list);
prom_bacnet_err_t prom_bacnet_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_BACNET_H */
