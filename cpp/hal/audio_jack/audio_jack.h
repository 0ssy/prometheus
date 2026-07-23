#ifndef PROMETHEUS_HAL_AUDIO_JACK_H
#define PROMETHEUS_HAL_AUDIO_JACK_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_AUDIO_JACK_MAX_DEVICES 128
#define PROM_AUDIO_JACK_PATH_MAX 256

typedef enum {
    PROM_AUDIO_JACK_OK = 0,
    PROM_AUDIO_JACK_ERR_INIT = -1,
    PROM_AUDIO_JACK_ERR_DEVICE_NOT_FOUND = -2,
    PROM_AUDIO_JACK_ERR_TRANSFER = -3,
    PROM_AUDIO_JACK_ERR_TIMEOUT = -4,
    PROM_AUDIO_JACK_ERR_MEMORY = -5,
} prom_audio_jack_err_t;

typedef struct {
    char path[PROM_AUDIO_JACK_PATH_MAX];
    uint32_t sample_rate;
    uint8_t channels;
    uint8_t bit_depth;
    char manufacturer[64];
    char product[64];
} prom_audio_jack_device_info_t;

typedef struct {
    prom_audio_jack_device_info_t devices[PROM_AUDIO_JACK_MAX_DEVICES];
    size_t count;
    prom_audio_jack_err_t error;
} prom_audio_jack_device_list_t;

prom_audio_jack_device_list_t prom_audio_jack_enumerate(void);
void prom_audio_jack_free_device_list(prom_audio_jack_device_list_t *list);
prom_audio_jack_err_t prom_audio_jack_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_AUDIO_JACK_H */
