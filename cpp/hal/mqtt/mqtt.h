#ifndef PROMETHEUS_HAL_MQTT_H
#define PROMETHEUS_HAL_MQTT_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_MQTT_MAX_DEVICES 128
#define PROM_MQTT_URL_MAX 256
#define PROM_MQTT_CLIENT_ID_MAX 128
#define PROM_MQTT_TOPIC_MAX 128

typedef enum {
    PROM_MQTT_OK = 0,
    PROM_MQTT_ERR_INIT = -1,
    PROM_MQTT_ERR_CONNECT = -2,
    PROM_MQTT_ERR_DEVICE_NOT_FOUND = -3,
    PROM_MQTT_ERR_TRANSFER = -4,
    PROM_MQTT_ERR_TIMEOUT = -5,
    PROM_MQTT_ERR_MEMORY = -6,
} prom_mqtt_err_t;

typedef struct {
    char url[PROM_MQTT_URL_MAX];
    char client_id[PROM_MQTT_CLIENT_ID_MAX];
    bool connected;
    char subscribed_topics[8][PROM_MQTT_TOPIC_MAX];
    size_t topic_count;
} prom_mqtt_device_info_t;

typedef struct {
    prom_mqtt_device_info_t devices[PROM_MQTT_MAX_DEVICES];
    size_t count;
    prom_mqtt_err_t error;
} prom_mqtt_device_list_t;

prom_mqtt_device_list_t prom_mqtt_enumerate(void);
void prom_mqtt_free_device_list(prom_mqtt_device_list_t *list);
prom_mqtt_err_t prom_mqtt_probe(const char *target);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_MQTT_H */
