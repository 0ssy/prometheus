#include "csi.h"
#include <string.h>
#include <stdio.h>

prom_csi_device_list_t prom_csi_enumerate(void) {
    prom_csi_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_CSI_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/video1");
    list.devices[0].lanes = 2;
    list.devices[0].refresh_rate_hz = 30;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "OmniVision");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "OV5647 CSI");
    list.count = 1;

    return list;
}

void prom_csi_free_device_list(prom_csi_device_list_t *list) {
    (void)list;
}

prom_csi_err_t prom_csi_probe(const char *target) {
    (void)target;
    return PROM_CSI_OK;
}
