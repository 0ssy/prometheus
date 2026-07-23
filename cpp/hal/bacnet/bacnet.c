#include "bacnet.h"
#include <string.h>
#include <stdio.h>

prom_bacnet_device_list_t prom_bacnet_enumerate(void) {
    prom_bacnet_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_BACNET_OK;

    list.devices[0].device_id = 1234;
    snprintf(list.devices[0].ip_address, sizeof(list.devices[0].ip_address), "192.168.1.100");
    list.devices[0].vendor_id = 8;
    list.devices[0].object_count = 12;
    list.count = 1;

    return list;
}

void prom_bacnet_free_device_list(prom_bacnet_device_list_t *list) {
    (void)list;
}

prom_bacnet_err_t prom_bacnet_probe(const char *target) {
    (void)target;
    return PROM_BACNET_OK;
}
