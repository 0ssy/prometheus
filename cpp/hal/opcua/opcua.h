#ifndef PROMETHEUS_HAL_OPCUA_H
#define PROMETHEUS_HAL_OPCUA_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_OPCUA_MAX_DEVICES 128
#define PROM_OPCUA_ENDPOINT_MAX 256

typedef enum {
    PROM_OPCUA_OK = 0,
    PROM_OPCUA_ERR_INIT = -1,
    PROM_OPCUA_ERR_DEVICE_NOT_FOUND = -2,
    PROM_OPCUA_ERR_TRANSFER = -3,
    PROM_OPCUA_ERR_TIMEOUT = -4,
    PROM_OPCUA_ERR_MEMORY = -5,
} prom_opcua_err_t;

typedef struct {
    char endpoint[PROM_OPCUA_ENDPOINT_MAX];
    uint32_t security_mode;
    bool connected;
} prom_opcua_device_info_t;

typedef struct {
    prom_opcua_device_info_t devices[PROM_OPCUA_MAX_DEVICES];
    size_t count;
    prom_opcua_err_t error;
} prom_opcua_device_list_t;

prom_opcua_device_list_t prom_opcua_enumerate(void);
void prom_opcua_free_device_list(prom_opcua_device_list_t *list);
prom_opcua_err_t prom_opcua_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_OPCUA_H */
