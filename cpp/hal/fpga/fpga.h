#ifndef PROMETHEUS_HAL_FPGA_H
#define PROMETHEUS_HAL_FPGA_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_FPGA_MAX_DEVICES 128
#define PROM_FPGA_PATH_MAX 256
#define PROM_FPGA_BITSTREAM_MAX 128

typedef enum {
    PROM_FPGA_OK = 0,
    PROM_FPGA_ERR_INIT = -1,
    PROM_FPGA_ERR_DEVICE_NOT_FOUND = -2,
    PROM_FPGA_ERR_TRANSFER = -3,
    PROM_FPGA_ERR_TIMEOUT = -4,
    PROM_FPGA_ERR_MEMORY = -5,
} prom_fpga_err_t;

typedef struct {
    char path[PROM_FPGA_PATH_MAX];
    uint16_t vendor_id;
    uint16_t product_id;
    char loaded_bitstream[PROM_FPGA_BITSTREAM_MAX];
    uint8_t logic_utilization_percent;
} prom_fpga_device_info_t;

typedef struct {
    prom_fpga_device_info_t devices[PROM_FPGA_MAX_DEVICES];
    size_t count;
    prom_fpga_err_t error;
} prom_fpga_device_list_t;

prom_fpga_device_list_t prom_fpga_enumerate(void);
void prom_fpga_free_device_list(prom_fpga_device_list_t *list);
prom_fpga_err_t prom_fpga_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_FPGA_H */
