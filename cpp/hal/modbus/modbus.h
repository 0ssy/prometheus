#ifndef PROMETHEUS_HAL_MODBUS_H
#define PROMETHEUS_HAL_MODBUS_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_MODBUS_MAX_DEVICES 128
#define PROM_MODBUS_PATH_MAX 256

typedef enum {
    PROM_MODBUS_OK = 0,
    PROM_MODBUS_ERR_INIT = -1,
    PROM_MODBUS_ERR_DEVICE_NOT_FOUND = -2,
    PROM_MODBUS_ERR_TRANSFER = -3,
    PROM_MODBUS_ERR_TIMEOUT = -4,
    PROM_MODBUS_ERR_MEMORY = -5,
} prom_modbus_err_t;

typedef struct {
    char path[PROM_MODBUS_PATH_MAX];
    uint8_t slave_id;
    uint32_t baud_rate;
    char parity;
    bool connected;
} prom_modbus_device_info_t;

typedef struct {
    prom_modbus_device_info_t devices[PROM_MODBUS_MAX_DEVICES];
    size_t count;
    prom_modbus_err_t error;
} prom_modbus_device_list_t;

prom_modbus_device_list_t prom_modbus_enumerate(void);
void prom_modbus_free_device_list(prom_modbus_device_list_t *list);
prom_modbus_err_t prom_modbus_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_MODBUS_H */
