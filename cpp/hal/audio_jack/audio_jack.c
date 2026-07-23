#include "audio_jack.h"
#include <string.h>
#include <stdio.h>

prom_audio_jack_device_list_t prom_audio_jack_enumerate(void) {
    prom_audio_jack_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_AUDIO_JACK_OK;

    snprintf(list.devices[0].path, sizeof(list.devices[0].path), "/dev/audio0");
    list.devices[0].sample_rate = 44100;
    list.devices[0].channels = 2;
    list.devices[0].bit_depth = 16;
    snprintf(list.devices[0].manufacturer, sizeof(list.devices[0].manufacturer), "Generic");
    snprintf(list.devices[0].product, sizeof(list.devices[0].product), "3.5mm Audio Jack");
    list.count = 1;

    return list;
}

void prom_audio_jack_free_device_list(prom_audio_jack_device_list_t *list) {
    (void)list;
}

prom_audio_jack_err_t prom_audio_jack_probe(const char *target) {
    (void)target;
    return PROM_AUDIO_JACK_OK;
}
