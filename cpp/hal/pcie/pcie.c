#include "pcie.h"
#include <string.h>
#include <stdio.h>

prom_pcie_device_list_t prom_pcie_enumerate(void) {
    prom_pcie_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_PCIE_OK;

    list.devices[0].bus = 0;
    list.devices[0].device = 2;
    list.devices[0].function = 0;
    list.devices[0].vendor_id = 0x144D;
    list.devices[0].product_id = 0xA808;
    list.devices[0].device_class = 1;
    list.devices[0].subclass = 8;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Samsung");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "NVMe SSD 990 PRO");
    list.count = 1;

    return list;
}

void prom_pcie_free_device_list(prom_pcie_device_list_t *list) {
    (void)list;
}

prom_pcie_err_t prom_pcie_probe(const char *target) {
    prom_pcie_device_list_t list = prom_pcie_enumerate();
    if (list.error != PROM_PCIE_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        char expected[64];
        snprintf(expected, sizeof(expected), "%04x:%04x",
            list.devices[i].vendor_id, list.devices[i].product_id);
        if (strstr(target, expected) != NULL) {
            return PROM_PCIE_OK;
        }
    }
    return PROM_PCIE_ERR_DEVICE_NOT_FOUND;
}
