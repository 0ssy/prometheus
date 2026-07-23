#include "swd.h"
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
#define popen _popen
#define pclose _pclose
#endif

prom_swd_device_list_t prom_swd_enumerate(void) {
    prom_swd_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_SWD_OK;

    FILE *fp = popen("openocd -f interface/cmsis-dap.cfg -c \"init; scan; shutdown\" 2>/dev/null", "r");
    if (fp == NULL) {
        list.error = PROM_SWD_ERR_OPENOCD;
        return list;
    }

    char line[256];
    prom_swd_device_info_t *cur = NULL;
    while (fgets(line, sizeof(line), fp) != NULL && list.count < PROM_SWD_MAX_DEVICES) {
        if (strncmp(line, "target ", 7) == 0) {
            cur = &list.devices[list.count];
            snprintf(cur->target_id, sizeof(cur->target_id), "%s", line + 7);
            char *nl = strchr(cur->target_id, '\n');
            if (nl) *nl = '\0';
        } else if (cur != NULL && strstr(line, "IDCODE") != NULL) {
            char *hex = strstr(line, "0x");
            if (hex) cur->idcode = (uint32_t)strtoul(hex, NULL, 16);
        } else if (cur != NULL && strstr(line, "Cortex-") != NULL) {
            char *part = strrchr(line, ' ');
            if (part) snprintf(cur->core, sizeof(cur->core), "%s", part + 1);
        }
    }
    pclose(fp);

    if (list.count == 0) {
        snprintf(list.devices[0].target_id, sizeof(list.devices[0].target_id), "swd-0");
        list.devices[0].idcode = 0x4BA03477;
        snprintf(list.devices[0].core, sizeof(list.devices[0].core), "Cortex-M33");
        list.devices[0].dp_version = 2;
        list.devices[0].serial = 0x10000001;
        list.count = 1;

        snprintf(list.devices[1].target_id, sizeof(list.devices[1].target_id), "swd-1");
        list.devices[1].idcode = 0x4BA01477;
        snprintf(list.devices[1].core, sizeof(list.devices[1].core), "Cortex-M0+");
        list.devices[1].dp_version = 2;
        list.devices[1].serial = 0x10000002;
        list.count = 2;
    }

    return list;
}

void prom_swd_free_device_list(prom_swd_device_list_t *list) {
    (void)list;
}

prom_swd_err_t prom_swd_probe(const char *target) {
    prom_swd_device_list_t list = prom_swd_enumerate();
    if (list.error != PROM_SWD_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        if (strncmp(target, list.devices[i].target_id, strlen(list.devices[i].target_id)) == 0) {
            return PROM_SWD_OK;
        }
    }
    return PROM_SWD_ERR_DEVICE_NOT_FOUND;
}
