#ifndef PROMETHEUS_HAL_DRONE_H
#define PROMETHEUS_HAL_DRONE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_DRONE_MAX_DEVICES 128
#define PROM_DRONE_SERIAL_MAX 64
#define PROM_DRONE_MODEL_MAX 64

typedef enum {
    PROM_DRONE_OK = 0,
    PROM_DRONE_ERR_INIT = -1,
    PROM_DRONE_ERR_DEVICE_NOT_FOUND = -2,
    PROM_DRONE_ERR_TRANSFER = -3,
    PROM_DRONE_ERR_TIMEOUT = -4,
    PROM_DRONE_ERR_MEMORY = -5,
} prom_drone_err_t;

typedef struct {
    char serial[PROM_DRONE_SERIAL_MAX];
    char model[PROM_DRONE_MODEL_MAX];
    uint8_t battery_level;
    bool gps_locked;
    bool armed;
} prom_drone_device_info_t;

typedef struct {
    prom_drone_device_info_t devices[PROM_DRONE_MAX_DEVICES];
    size_t count;
    prom_drone_err_t error;
} prom_drone_device_list_t;

prom_drone_device_list_t prom_drone_enumerate(void);
void prom_drone_free_device_list(prom_drone_device_list_t *list);
prom_drone_err_t prom_drone_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_DRONE_H */
