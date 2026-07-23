#ifndef PROMETHEUS_HAL_MIDI_H
#define PROMETHEUS_HAL_MIDI_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_MIDI_MAX_DEVICES 128
#define PROM_MIDI_PATH_MAX 256

typedef enum {
    PROM_MIDI_OK = 0,
    PROM_MIDI_ERR_INIT = -1,
    PROM_MIDI_ERR_DEVICE_NOT_FOUND = -2,
    PROM_MIDI_ERR_TRANSFER = -3,
    PROM_MIDI_ERR_TIMEOUT = -4,
    PROM_MIDI_ERR_MEMORY = -5,
} prom_midi_err_t;

typedef struct {
    char path[PROM_MIDI_PATH_MAX];
    uint8_t midi_channel_count;
    bool has_transpose;
    char manufacturer[64];
    char product[64];
} prom_midi_device_info_t;

typedef struct {
    prom_midi_device_info_t devices[PROM_MIDI_MAX_DEVICES];
    size_t count;
    prom_midi_err_t error;
} prom_midi_device_list_t;

prom_midi_device_list_t prom_midi_enumerate(void);
void prom_midi_free_device_list(prom_midi_device_list_t *list);
prom_midi_err_t prom_midi_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_MIDI_H */
