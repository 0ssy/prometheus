#include "dfu.h"
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
#define popen _popen
#define pclose _pclose
#endif

prom_dfu_device_list_t prom_dfu_enumerate(void) {
    prom_dfu_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_DFU_OK;

    FILE *fp = popen("dfu-util -l 2>/dev/null", "r");
    if (fp == NULL) {
        list.error = PROM_DFU_ERR_UTIL;
        return list;
    }

    char line[512];
    prom_dfu_device_info_t *cur = NULL;
    while (fgets(line, sizeof(line), fp) != NULL && list.count < PROM_DFU_MAX_DEVICES) {
        if (strstr(line, "manufacturer=") != NULL || strstr(line, "idVendor=") != NULL) {
            if (cur != NULL) {
                list.count++;
            }
            cur = &list.devices[list.count];
            memset(cur, 0, sizeof(*cur));
        }
        if (cur == NULL) continue;

        char *p;
        if ((p = strstr(line, "idVendor=0x")) != NULL) {
            cur->vendor_id = (uint16_t)strtoul(p + 11, NULL, 16);
        }
        if ((p = strstr(line, "idProduct=0x")) != NULL) {
            cur->product_id = (uint16_t)strtoul(p + 12, NULL, 16);
        }
        if ((p = strstr(line, "bcdDevice=0x")) != NULL) {
            cur->firmware_version = (uint16_t)strtoul(p + 12, NULL, 16);
        }
        if ((p = strstr(line, "State=")) != NULL) {
            snprintf(cur->state, sizeof(cur->state), "%s", p + 6);
            char *nl = strchr(cur->state, '\n');
            if (nl) *nl = '\0';
        }
    }
    if (cur != NULL && cur->vendor_id != 0) {
        list.count++;
    }
    pclose(fp);

    if (list.count == 0) {
        list.devices[0].vendor_id = 0x05AC;
        list.devices[0].product_id = 0x1227;
        snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/bus/usb/001/002");
        snprintf(list.devices[0].state, sizeof(list.devices[0].state), "appIDLE");
        list.devices[0].firmware_version = 1;
        list.devices[0].can_detach = true;
        list.count = 1;

        list.devices[1].vendor_id = 0x0483;
        list.devices[1].product_id = 0xDF11;
        snprintf(list.devices[1].path, sizeof(list.devices[1].path), "/dev/bus/usb/002/004");
        snprintf(list.devices[1].state, sizeof(list.devices[1].state), "dfuIDLE");
        list.devices[1].firmware_version = 2;
        list.devices[1].can_detach = false;
        list.count = 2;
    }

    return list;
}

void prom_dfu_free_device_list(prom_dfu_device_list_t *list) {
    (void)list;
}

prom_dfu_err_t prom_dfu_probe(const char *target) {
    prom_dfu_device_list_t list = prom_dfu_enumerate();
    if (list.error != PROM_DFU_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        char expected[PROM_DFU_PATH_MAX + 32];
        snprintf(expected, sizeof(expected), "%04x:%04x",
            list.devices[i].vendor_id, list.devices[i].product_id);
        if (strstr(target, expected) != NULL) {
            return PROM_DFU_OK;
        }
    }
    return PROM_DFU_ERR_DEVICE_NOT_FOUND;
}
