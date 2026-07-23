#ifndef PROMETHEUS_HAL_PCIE_H
#define PROMETHEUS_HAL_PCIE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_PCIE_MAX_DEVICES 128

typedef enum {
    PROM_PCIE_OK = 0,
    PROM_PCIE_ERR_INIT = -1,
    PROM_PCIE_ERR_DEVICE_NOT_FOUND = -2,
    PROM_PCIE_ERR_TRANSFER = -3,
    PROM_PCIE_ERR_TIMEOUT = -4,
    PROM_PCIE_ERR_MEMORY = -5,
} prom_pcie_err_t;

typedef struct {
    uint8_t bus;
    uint8_t device;
    uint8_t function;
    uint16_t vendor_id;
    uint16_t product_id;
    uint8_t device_class;
    uint8_t subclass;
    char manufacturer[64];
    char product[64];
} prom_pcie_device_info_t;

typedef struct {
    prom_pcie_device_info_t devices[PROM_PCIE_MAX_DEVICES];
    size_t count;
    prom_pcie_err_t error;
} prom_pcie_device_list_t;

prom_pcie_device_list_t prom_pcie_enumerate(void);
void prom_pcie_free_device_list(prom_pcie_device_list_t *list);
prom_pcie_err_t prom_pcie_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_PCIE_H */
