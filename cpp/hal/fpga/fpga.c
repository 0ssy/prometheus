#include "fpga.h"
#include <string.h>
#include <stdio.h>

prom_fpga_device_list_t prom_fpga_enumerate(void) {
    prom_fpga_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_FPGA_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/fpga0");
    list.devices[0].vendor_id = 0x10EE;
    list.devices[0].product_id = 0x0201;
    snprintf(list.devices[0].loaded_bitstream, sizeof(list.devices[0].loaded_bitstream), "top.bit");
    list.devices[0].logic_utilization_percent = 45;
    list.count = 1;

    return list;
}

void prom_fpga_free_device_list(prom_fpga_device_list_t *list) {
    (void)list;
}

prom_fpga_err_t prom_fpga_probe(const char *target) {
    (void)target;
    return PROM_FPGA_OK;
}
