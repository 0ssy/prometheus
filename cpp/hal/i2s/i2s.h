#ifndef PROMETHEUS_HAL_I2S_H
#define PROMETHEUS_HAL_I2S_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_I2S_MAX_DEVICES 128
#define PROM_I2S_PATH_MAX 256

typedef enum {
    PROM_I2S_OK = 0,
    PROM_I2S_ERR_INIT = -1,
    PROM_I2S_ERR_DEVICE_NOT_FOUND = -2,
    PROM_I2S_ERR_TRANSFER = -3,
    PROM_I2S_ERR_TIMEOUT = -4,
    PROM_I2S_ERR_MEMORY = -5,
} prom_i2s_err_t;

typedef struct {
    char path[PROM_I2S_PATH_MAX];
    uint32_t sample_rate;
    uint8_t channels;
    uint8_t bit_depth;
    char manufacturer[64];
    char product[64];
} prom_i2s_device_info_t;

typedef struct {
    prom_i2s_device_info_t devices[PROM_I2S_MAX_DEVICES];
    size_t count;
    prom_i2s_err_t error;
} prom_i2s_device_list_t;

prom_i2s_device_list_t prom_i2s_enumerate(void);
void prom_i2s_free_device_list(prom_i2s_device_list_t *list);
prom_i2s_err_t prom_i2s_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_I2S_H */
