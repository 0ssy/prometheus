#include "vehicle.h"
#include <string.h>
#include <stdio.h>

prom_vehicle_device_list_t prom_vehicle_enumerate(void) {
    prom_vehicle_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_VEHICLE_OK;

    snprintf(list.devices[0].vin, sizeof(list.devices[0].vin), "1HGBH41JXMN109186");
    snprintf(list.devices[0].make, sizeof(list.devices[0].make), "Honda");
    snprintf(list.devices[0].model, sizeof(list.devices[0].model), "Civic");
    snprintf(list.devices[0].obd_interface, sizeof(list.devices[0].obd_interface), "OBD-II");
    list.devices[0].connected = true;
    list.count = 1;

    return list;
}

void prom_vehicle_free_device_list(prom_vehicle_device_list_t *list) {
    (void)list;
}

prom_vehicle_err_t prom_vehicle_probe(const char *target) {
    (void)target;
    return PROM_VEHICLE_OK;
}
