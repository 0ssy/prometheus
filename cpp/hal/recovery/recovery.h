#ifndef PROMETHEUS_HAL_RECOVERY_H
#define PROMETHEUS_HAL_RECOVERY_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_RECOVERY_MAX_DEVICES 128
#define PROM_RECOVERY_ID_MAX 64

typedef enum {
    PROM_RECOVERY_ANDROID = 0,
    PROM_RECOVERY_EDL,
    PROM_RECOVERY_ODIN,
    PROM_RECOVERY_DFU,
    PROM_RECOVERY_BIOS,
    PROM_RECOVERY_UEFI,
    PROM_RECOVERY_TPM,
    PROM_RECOVERY_ROUTER,
    PROM_RECOVERY_IOT,
    PROM_RECOVERY_DRONE,
    PROM_RECOVERY_VEHICLE,
    PROM_RECOVERY_ECU,
    PROM_RECOVERY_EEPROM,
    PROM_RECOVERY_NAND,
    PROM_RECOVERY_NOR,
    PROM_RECOVERY_SPI_FLASH,
    PROM_RECOVERY_EMBEDDED_LINUX,
    PROM_RECOVERY_MODE_COUNT
} prom_recovery_mode_t;

typedef struct {
    prom_recovery_mode_t mode;
    char device_id[PROM_RECOVERY_ID_MAX];
    char product[64];
    char status[32];
} prom_recovery_device_info_t;

typedef struct {
    prom_recovery_device_info_t devices[PROM_RECOVERY_MAX_DEVICES];
    size_t count;
    int error;
} prom_recovery_device_list_t;

prom_recovery_device_list_t prom_recovery_enumerate(prom_recovery_mode_t mode);
void prom_recovery_free_device_list(prom_recovery_device_list_t *list);
int prom_recovery_probe(const char *target, prom_recovery_mode_t *out_mode);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_RECOVERY_H */
