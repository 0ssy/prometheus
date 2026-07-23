#include "hid.h"
#include <string.h>
#include <stdio.h>

#ifdef HAVE_HIDAPI
#include <hidapi.h>
#endif

prom_hid_device_list_t prom_hid_enumerate(void) {
    prom_hid_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_HID_OK;

#ifdef HAVE_HIDAPI
    if (hid_init() != 0) {
        list.error = PROM_HID_ERR_INIT;
        return list;
    }

    struct hid_device_info *devs = hid_enumerate(0, 0);
    for (struct hid_device_info *d = devs; d != NULL && list.count < PROM_HID_MAX_DEVICES; d = d->next) {
        prom_hid_device_info_t *info = &list.devices[list.count];
        snprintf(info->path, sizeof(info->path), "%s", d->path);
        info->vendor_id = (uint16_t)d->vendor_id;
        info->product_id = (uint16_t)d->product_id;
        info->usage_page = (uint16_t)d->usage_page;
        info->usage_id = (uint16_t)d->usage;
        info->interface_number = (uint8_t)d->interface_number;
        if (d->manufacturer_string) snprintf(info->manufacturer, sizeof(info->manufacturer), "%ls", d->manufacturer_string);
        if (d->product_string) snprintf(info->product, sizeof(info->product), "%ls", d->product_string);
        if (d->serial_number) snprintf(info->serial_number, sizeof(info->serial_number), "%ls", d->serial_number);
        list.count++;
    }
    hid_free_enumeration(devs);
    hid_exit();
#else
    list.devices[0].vendor_id = 0x046D;
    list.devices[0].product_id = 0xC52B;
    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/hidraw0");
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Logitech");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "Unifying Receiver");
    snprintf(list.devices[0].serial_number, sizeof(list.devices[0].serial_number), "12345678");
    list.devices[0].usage_page = 0x01;
    list.devices[0].usage_id = 0x02;
    list.devices[0].interface_number = 0;
    list.count = 1;

    list.devices[1].vendor_id = 0x0C45;
    list.devices[1].product_id = 0x6366;
    snprintf(list.devices[1].path, sizeof(list.devices[1].path), "/dev/hidraw1");
    snprintf(list.devices[1].manufacturer, sizeof(list.devices[1].manufacturer), "Microdia");
    snprintf(list.devices[1].product, sizeof(list.devices[1].product), "USB Keyboard");
    list.devices[1].usage_page = 0x01;
    list.devices[1].usage_id = 0x06;
    list.devices[1].interface_number = 0;
    list.count = 2;
#endif

    return list;
}

void prom_hid_free_device_list(prom_hid_device_list_t *list) {
    (void)list;
}

prom_hid_err_t prom_hid_probe(const char *target) {
    prom_hid_device_list_t list = prom_hid_enumerate();
    if (list.error != PROM_HID_OK) return list.error;

    for (size_t i = 0; i < list.count; i++) {
        char expected[PROM_HID_PATH_MAX + 32];
        snprintf(expected, sizeof(expected), "%04x:%04x",
            list.devices[i].vendor_id, list.devices[i].product_id);
        if (strstr(target, expected) != NULL) {
            return PROM_HID_OK;
        }
        if (strcmp(target, list.devices[i].path) == 0) {
            return PROM_HID_OK;
        }
    }
    return PROM_HID_ERR_DEVICE_NOT_FOUND;
}
