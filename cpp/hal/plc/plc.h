#ifndef PROMETHEUS_HAL_PLC_H
#define PROMETHEUS_HAL_PLC_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_PLC_MAX_DEVICES 128
#define PROM_PLC_PATH_MAX 256
#define PROM_PLC_IP_MAX 64
#define PROM_PLC_MANUFACTURER_MAX 64
#define PROM_PLC_MODEL_MAX 64
#define PROM_PLC_PROTOCOL_MAX 32

typedef enum {
    PROM_PLC_OK = 0,
    PROM_PLC_ERR_INIT = -1,
    PROM_PLC_ERR_DEVICE_NOT_FOUND = -2,
    PROM_PLC_ERR_TRANSFER = -3,
    PROM_PLC_ERR_TIMEOUT = -4,
    PROM_PLC_ERR_MEMORY = -5,
} prom_plc_err_t;

typedef struct {
    char path[PROM_PLC_PATH_MAX];
    char manufacturer[PROM_PLC_MANUFACTURER_MAX];
    char model[PROM_PLC_MODEL_MAX];
    char protocol[PROM_PLC_PROTOCOL_MAX];
    char ip_address[PROM_PLC_IP_MAX];
    bool connected;
} prom_plc_device_info_t;

typedef struct {
    prom_plc_device_info_t devices[PROM_PLC_MAX_DEVICES];
    size_t count;
    prom_plc_err_t error;
} prom_plc_device_list_t;

prom_plc_device_list_t prom_plc_enumerate(void);
void prom_plc_free_device_list(prom_plc_device_list_t *list);
prom_plc_err_t prom_plc_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_PLC_H */
