#ifndef PROMETHEUS_HAL_HDMI_H
#define PROMETHEUS_HAL_HDMI_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_HDMI_MAX_DEVICES 128
#define PROM_HDMI_PATH_MAX 256

typedef enum {
    PROM_HDMI_OK = 0,
    PROM_HDMI_ERR_INIT = -1,
    PROM_HDMI_ERR_DEVICE_NOT_FOUND = -2,
    PROM_HDMI_ERR_TRANSFER = -3,
    PROM_HDMI_ERR_TIMEOUT = -4,
    PROM_HDMI_ERR_MEMORY = -5,
} prom_hdmi_err_t;

typedef struct {
    char path[PROM_HDMI_PATH_MAX];
    uint16_t width;
    uint16_t height;
    uint32_t refresh_rate_hz;
    char manufacturer[64];
    char product[64];
} prom_hdmi_device_info_t;

typedef struct {
    prom_hdmi_device_info_t devices[PROM_HDMI_MAX_DEVICES];
    size_t count;
    prom_hdmi_err_t error;
} prom_hdmi_device_list_t;

prom_hdmi_device_list_t prom_hdmi_enumerate(void);
void prom_hdmi_free_device_list(prom_hdmi_device_list_t *list);
prom_hdmi_err_t prom_hdmi_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_HDMI_H */
