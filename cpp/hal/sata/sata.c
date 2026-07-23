#include "sata.h"
#include <string.h>
#include <stdio.h>

prom_sata_device_list_t prom_sata_enumerate(void) {
    prom_sata_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_SATA_OK;

    snprintf(list.devices[0].port, sizeof(list.devices[0].port), "ata1");
    snprintf(list.devices[0].model, sizeof(list.devices[0].model), "CT500P1SSD8");
    snprintf(list.devices[0].serial, sizeof(list.devices[0].serial), "210123456ABC");
    snprintf(list.devices[0].firmware_version, sizeof(list.devices[0].firmware_version), "P1CR010");
    list.devices[0].capacity_bytes = 500107862016ULL;
    list.count = 1;

    return list;
}

void prom_sata_free_device_list(prom_sata_device_list_t *list) {
    (void)list;
}

prom_sata_err_t prom_sata_probe(const char *target) {
    prom_sata_device_list_t list = prom_sata_enumerate();
    if (list.error != PROM_SATA_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        if (strstr(target, list.devices[i].model) != NULL) {
            return PROM_SATA_OK;
        }
    }
    return PROM_SATA_ERR_DEVICE_NOT_FOUND;
}
