#include "plc.h"
#include <string.h>
#include <stdio.h>

prom_plc_device_list_t prom_plc_enumerate(void) {
    prom_plc_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_PLC_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "plc0");
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Siemens");
    snprintf(list.devices[0].model, sizeof(list.devices[0].model), "S7-1500");
    snprintf(list.devices[0].protocol, sizeof(list.devices[0].protocol), "S7");
    snprintf(list.devices[0].ip_address, sizeof(list.devices[0].ip_address), "192.168.0.1");
    list.devices[0].connected = true;
    list.count = 1;

    return list;
}

void prom_plc_free_device_list(prom_plc_device_list_t *list) {
    (void)list;
}

prom_plc_err_t prom_plc_probe(const char *target) {
    (void)target;
    return PROM_PLC_OK;
}
