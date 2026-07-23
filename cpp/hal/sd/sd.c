#include "sd.h"
#include <string.h>
#include <stdio.h>

prom_sd_device_list_t prom_sd_enumerate(void) {
    prom_sd_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_SD_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/mmcblk0");
    list.devices[0].capacity_bytes = 32000000000ULL;
    list.devices[0].speed_class = 10;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "SanDisk");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "Ultra 32GB");
    list.count = 1;

    return list;
}

void prom_sd_free_device_list(prom_sd_device_list_t *list) {
    (void)list;
}

prom_sd_err_t prom_sd_probe(const char *target) {
    (void)target;
    return PROM_SD_OK;
}
