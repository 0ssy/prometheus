#include "opcua.h"
#include <string.h>
#include <stdio.h>

prom_opcua_device_list_t prom_opcua_enumerate(void) {
    prom_opcua_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_OPCUA_OK;

    snprintf(list.devices[0].endpoint, sizeof(list.devices[0].endpoint), "opc.tcp://localhost:4840");
    list.devices[0].security_mode = 1;
    list.devices[0].connected = true;
    list.count = 1;

    return list;
}

void prom_opcua_free_device_list(prom_opcua_device_list_t *list) {
    (void)list;
}

prom_opcua_err_t prom_opcua_probe(const char *target) {
    (void)target;
    return PROM_OPCUA_OK;
}
