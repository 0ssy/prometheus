#include "midi.h"
#include <string.h>
#include <stdio.h>

prom_midi_device_list_t prom_midi_enumerate(void) {
    prom_midi_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_MIDI_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/midi0");
    list.devices[0].midi_channel_count = 16;
    list.devices[0].has_transpose = true;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Roland");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "UM-ONE");
    list.count = 1;

    return list;
}

void prom_midi_free_device_list(prom_midi_device_list_t *list) {
    (void)list;
}

prom_midi_err_t prom_midi_probe(const char *target) {
    (void)target;
    return PROM_MIDI_OK;
}
