#include "i2s.h"
#include <string.h>
#include <stdio.h>

prom_i2s_device_list_t prom_i2s_enumerate(void) {
    prom_i2s_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_I2S_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/i2s0");
    list.devices[0].sample_rate = 48000;
    list.devices[0].channels = 2;
    list.devices[0].bit_depth = 16;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Analog Devices");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "I2S DAC");
    list.count = 1;

    return list;
}

void prom_i2s_free_device_list(prom_i2s_device_list_t *list) {
    (void)list;
}

prom_i2s_err_t prom_i2s_probe(const char *target) {
    (void)target;
    return PROM_I2S_OK;
}
