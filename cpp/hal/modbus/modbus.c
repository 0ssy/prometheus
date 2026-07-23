#include "modbus.h"
#include <string.h>
#include <stdio.h>

prom_modbus_device_list_t prom_modbus_enumerate(void) {
    prom_modbus_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_MODBUS_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/ttyUSB0");
    list.devices[0].slave_id = 1;
    list.devices[0].baud_rate = 9600;
    list.devices[0].parity = 'N';
    list.devices[0].connected = true;
    list.count = 1;

    return list;
}

void prom_modbus_free_device_list(prom_modbus_device_list_t *list) {
    (void)list;
}

prom_modbus_err_t prom_modbus_probe(const char *target) {
    (void)target;
    return PROM_MODBUS_OK;
}
