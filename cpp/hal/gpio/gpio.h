#ifndef PROMETHEUS_HAL_GPIO_H
#define PROMETHEUS_HAL_GPIO_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_GPIO_MAX_PINS 512
#define PROM_GPIO_MAX_CHIPS 32

typedef enum {
    PROM_GPIO_EDGE_NONE = 0,
    PROM_GPIO_EDGE_RISING = 1,
    PROM_GPIO_EDGE_FALLING = 2,
    PROM_GPIO_EDGE_BOTH = 3,
} prom_gpio_edge_t;

typedef enum {
    PROM_GPIO_DIR_IN = 0,
    PROM_GPIO_DIR_OUT = 1,
    PROM_GPIO_DIR_BOTH = 2,
} prom_gpio_dir_t;

typedef enum {
    PROM_GPIO_DRIVE_PUSH_PULL = 0,
    PROM_GPIO_DRIVE_OPEN_DRAIN = 1,
    PROM_GPIO_DRIVE_OPEN_SOURCE = 2,
} prom_gpio_drive_t;

typedef enum {
    PROM_GPIO_OK = 0,
    PROM_GPIO_ERR_CHIP = -1,
    PROM_GPIO_ERR_PIN = -2,
    PROM_GPIO_ERR_EXPORT = -3,
    PROM_GPIO_ERR_DIRECTION = -4,
    PROM_GPIO_ERR_VALUE = -5,
    PROM_GPIO_ERR_EDGE = -6,
    PROM_GPIO_ERR_NOT_SUPPORTED = -7,
} prom_gpio_err_t;

typedef struct {
    uint32_t chip_id;
    char label[32];
    uint32_t base;
    uint32_t num_pins;
} prom_gpio_chip_info_t;

typedef struct {
    prom_gpio_chip_info_t chips[PROM_GPIO_MAX_CHIPS];
    size_t chip_count;
    prom_gpio_err_t error;
} prom_gpio_chip_list_t;

typedef struct {
    uint32_t chip_id;
    uint32_t pin;
    prom_gpio_dir_t direction;
    bool value;
    prom_gpio_edge_t edge;
    prom_gpio_drive_t drive;
    bool is_exported;
} prom_gpio_pin_info_t;

prom_gpio_chip_list_t prom_gpio_list_chips(void);
void prom_gpio_free_chip_list(prom_gpio_chip_list_t *list);
prom_gpio_err_t prom_gpio_export(uint32_t chip_id, uint32_t pin);
prom_gpio_err_t prom_gpio_unexport(uint32_t chip_id, uint32_t pin);
prom_gpio_err_t prom_gpio_set_direction(uint32_t chip_id, uint32_t pin, prom_gpio_dir_t dir);
prom_gpio_err_t prom_gpio_set_value(uint32_t chip_id, uint32_t pin, bool value);
prom_gpio_err_t prom_gpio_get_value(uint32_t chip_id, uint32_t pin, bool *value);
prom_gpio_err_t prom_gpio_set_edge(uint32_t chip_id, uint32_t pin, prom_gpio_edge_t edge);
prom_gpio_pin_info_t prom_gpio_get_pin_info(uint32_t chip_id, uint32_t pin);
const char *prom_gpio_strerror(prom_gpio_err_t err);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_GPIO_H */
