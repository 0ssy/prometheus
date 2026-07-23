#include "hdmi.h"
#include <string.h>
#include <stdio.h>

prom_hdmi_device_list_t prom_hdmi_enumerate(void) {
    prom_hdmi_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_HDMI_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/hdmi0");
    list.devices[0].width = 1920;
    list.devices[0].height = 1080;
    list.devices[0].refresh_rate_hz = 60;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "DEL");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "DELL P2419H");
    list.count = 1;

    return list;
}

void prom_hdmi_free_device_list(prom_hdmi_device_list_t *list) {
    (void)list;
}

prom_hdmi_err_t prom_hdmi_probe(const char *target) {
    (void)target;
    return PROM_HDMI_OK;
}
