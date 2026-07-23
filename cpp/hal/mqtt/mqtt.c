#include "mqtt.h"
#include <string.h>
#include <stdio.h>

prom_mqtt_device_list_t prom_mqtt_enumerate(void) {
    prom_mqtt_device_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_MQTT_OK;

    snprintf(list.devices[0].url, sizeof(list.devices[0].url), "mqtt://localhost:1883");
    snprintf(list.devices[0].client_id, sizeof(list.devices[0].client_id), "prometheus-mqtt-0");
    list.devices[0].connected = true;
    snprintf(list.devices[0].subscribed_topics[0], sizeof(list.devices[0].subscribed_topics[0]), "sensors/temperature");
    snprintf(list.devices[0].subscribed_topics[1], sizeof(list.devices[0].subscribed_topics[1]), "devices/status");
    list.devices[0].topic_count = 2;
    list.count = 1;

    return list;
}

void prom_mqtt_free_device_list(prom_mqtt_device_list_t *list) {
    (void)list;
}

prom_mqtt_err_t prom_mqtt_probe(const char *target) {
    (void)target;
    return PROM_MQTT_OK;
}
