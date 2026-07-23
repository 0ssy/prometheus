#ifndef PROMETHEUS_HAL_VEHICLE_H
#define PROMETHEUS_HAL_VEHICLE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_VEHICLE_MAX_DEVICES 128
#define PROM_VEHICLE_VIN_MAX 32
#define PROM_VEHICLE_MAKE_MAX 32
#define PROM_VEHICLE_MODEL_MAX 32
#define PROM_VEHICLE_OBD_MAX 32

typedef enum {
    PROM_VEHICLE_OK = 0,
    PROM_VEHICLE_ERR_INIT = -1,
    PROM_VEHICLE_ERR_DEVICE_NOT_FOUND = -2,
    PROM_VEHICLE_ERR_TRANSFER = -3,
    PROM_VEHICLE_ERR_TIMEOUT = -4,
    PROM_VEHICLE_ERR_MEMORY = -5,
} prom_vehicle_err_t;

typedef struct {
    char vin[PROM_VEHICLE_VIN_MAX];
    char make[PROM_VEHICLE_MAKE_MAX];
    char model[PROM_VEHICLE_MODEL_MAX];
    char obd_interface[PROM_VEHICLE_OBD_MAX];
    bool connected;
} prom_vehicle_device_info_t;

typedef struct {
    prom_vehicle_device_info_t devices[PROM_VEHICLE_MAX_DEVICES];
    size_t count;
    prom_vehicle_err_t error;
} prom_vehicle_device_list_t;

prom_vehicle_device_list_t prom_vehicle_enumerate(void);
void prom_vehicle_free_device_list(prom_vehicle_device_list_t *list);
prom_vehicle_err_t prom_vehicle_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_VEHICLE_H */
