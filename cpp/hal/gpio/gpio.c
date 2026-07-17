#include "gpio.h"
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <dirent.h>
#endif

prom_gpio_chip_list_t prom_gpio_list_chips(void) {
    prom_gpio_chip_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_GPIO_OK;

#ifdef _WIN32
    list.chips[0].chip_id = 0;
    snprintf(list.chips[0].label, sizeof(list.chips[0].label), "gpio0");
    list.chips[0].base = 0;
    list.chips[0].num_pins = 16;
    list.chip_count = 1;
#else
    DIR *dir = opendir("/sys/class/gpio");
    if (!dir) {
        list.error = PROM_GPIO_ERR_CHIP;
        return list;
    }

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL && list.chip_count < PROM_GPIO_MAX_CHIPS) {
        if (entry->d_name[0] == '.') continue;

        char path[512];
        char chip_path[512];
        snprintf(path, sizeof(path), "/sys/class/gpio/%s", entry->d_name);

        struct stat st;
        if (stat(path, &st) != 0 || !S_ISDIR(st.st_mode)) continue;

        snprintf(chip_path, sizeof(chip_path), "%s/label", path);
        int fd = open(chip_path, O_RDONLY);
        if (fd >= 0) {
            char label[32] = {0};
            read(fd, label, sizeof(label) - 1);
            close(fd);

            char *newline = strchr(label, '\n');
            if (newline) *newline = '\0';

            list.chips[list.chip_count].chip_id = (uint32_t)list.chip_count;
            snprintf(list.chips[list.chip_count].label, sizeof(list.chips[list.chip_count].label), "%s", label);
            list.chips[list.chip_count].base = 0;
            list.chips[list.chip_count].num_pins = 32;
            list.chip_count++;
        }
    }

    closedir(dir);
#endif

    return list;
}

void prom_gpio_free_chip_list(prom_gpio_chip_list_t *list) {
    (void)list;
}

prom_gpio_err_t prom_gpio_export(uint32_t chip_id, uint32_t pin) {
    (void)chip_id;
    (void)pin;
#ifdef _WIN32
    return PROM_GPIO_OK;
#else
    char path[64];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%u/export", pin);
    int fd = open(path, O_WRONLY);
    if (fd < 0) return PROM_GPIO_ERR_EXPORT;
    close(fd);
    return PROM_GPIO_OK;
#endif
}

prom_gpio_err_t prom_gpio_unexport(uint32_t chip_id, uint32_t pin) {
    (void)chip_id;
    (void)pin;
#ifdef _WIN32
    return PROM_GPIO_OK;
#else
    char path[64];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%u/unexport", pin);
    int fd = open(path, O_WRONLY);
    if (fd < 0) return PROM_GPIO_ERR_EXPORT;
    close(fd);
    return PROM_GPIO_OK;
#endif
}

prom_gpio_err_t prom_gpio_set_direction(uint32_t chip_id, uint32_t pin, prom_gpio_dir_t dir) {
    (void)chip_id;
    (void)pin;
    (void)dir;
#ifdef _WIN32
    return PROM_GPIO_OK;
#else
    char path[64];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%u/direction", pin);
    int fd = open(path, O_WRONLY);
    if (fd < 0) return PROM_GPIO_ERR_DIRECTION;
    const char *direction = (dir == PROM_GPIO_DIR_OUT) ? "out" : "in";
    write(fd, direction, strlen(direction));
    close(fd);
    return PROM_GPIO_OK;
#endif
}

prom_gpio_err_t prom_gpio_set_value(uint32_t chip_id, uint32_t pin, bool value) {
    (void)chip_id;
    (void)pin;
    (void)value;
#ifdef _WIN32
    return PROM_GPIO_OK;
#else
    char path[64];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%u/value", pin);
    int fd = open(path, O_WRONLY);
    if (fd < 0) return PROM_GPIO_ERR_VALUE;
    const char *val = value ? "1" : "0";
    write(fd, val, 1);
    close(fd);
    return PROM_GPIO_OK;
#endif
}

prom_gpio_err_t prom_gpio_get_value(uint32_t chip_id, uint32_t pin, bool *value) {
    (void)chip_id;
    (void)pin;
    (void)value;
#ifdef _WIN32
    if (value) *value = false;
    return PROM_GPIO_OK;
#else
    char path[64];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%u/value", pin);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return PROM_GPIO_ERR_VALUE;
    char buf[2] = {0};
    read(fd, buf, 1);
    close(fd);
    if (value) *value = (buf[0] == '1');
    return PROM_GPIO_OK;
#endif
}

prom_gpio_err_t prom_gpio_set_edge(uint32_t chip_id, uint32_t pin, prom_gpio_edge_t edge) {
    (void)chip_id;
    (void)pin;
    (void)edge;
#ifdef _WIN32
    return PROM_GPIO_OK;
#else
    char path[64];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%u/edge", pin);
    int fd = open(path, O_WRONLY);
    if (fd < 0) return PROM_GPIO_ERR_EDGE;
    const char *edge_str = "none";
    switch (edge) {
        case PROM_GPIO_EDGE_RISING: edge_str = "rising"; break;
        case PROM_GPIO_EDGE_FALLING: edge_str = "falling"; break;
        case PROM_GPIO_EDGE_BOTH: edge_str = "both"; break;
        default: break;
    }
    write(fd, edge_str, strlen(edge_str));
    close(fd);
    return PROM_GPIO_OK;
#endif
}

prom_gpio_pin_info_t prom_gpio_get_pin_info(uint32_t chip_id, uint32_t pin) {
    prom_gpio_pin_info_t info;
    memset(&info, 0, sizeof(info));
    info.chip_id = chip_id;
    info.pin = pin;
    info.direction = PROM_GPIO_DIR_IN;
    info.value = false;
    info.edge = PROM_GPIO_EDGE_NONE;
    info.drive = PROM_GPIO_DRIVE_PUSH_PULL;
    info.is_exported = false;
    return info;
}

const char *prom_gpio_strerror(prom_gpio_err_t err) {
    switch (err) {
        case PROM_GPIO_OK: return "OK";
        case PROM_GPIO_ERR_CHIP: return "chip not found";
        case PROM_GPIO_ERR_PIN: return "pin not found";
        case PROM_GPIO_ERR_EXPORT: return "export failed";
        case PROM_GPIO_ERR_DIRECTION: return "direction set failed";
        case PROM_GPIO_ERR_VALUE: return "value read/write failed";
        case PROM_GPIO_ERR_EDGE: return "edge detect not supported";
        case PROM_GPIO_ERR_NOT_SUPPORTED: return "not supported on this platform";
        default: return "unknown error";
    }
}
