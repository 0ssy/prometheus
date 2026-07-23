#include "drone.h"
#include <string.h>
#include <stdio.h>

prom_drone_device_list_t prom_drone_enumerate(void) {
    prom_drone_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_DRONE_OK;

    snprintf(list.devices[0].serial, sizeof(list.devices[0].serial), "DRONE-001");
    snprintf(list.devices[0].model, sizeof(list.devices[0].model), "Quad-X F450");
    list.devices[0].battery_level = 85;
    list.devices[0].gps_locked = true;
    list.devices[0].armed = false;
    list.count = 1;

    return list;
}

void prom_drone_free_device_list(prom_drone_device_list_t *list) {
    (void)list;
}

prom_drone_err_t prom_drone_probe(const char *target) {
    (void)target;
    return PROM_DRONE_OK;
}
