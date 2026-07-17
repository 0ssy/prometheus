#ifndef PROMETHEUS_HAL_SERIAL_H
#define PROMETHEUS_HAL_SERIAL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PROM_SERIAL_MAX_PORTS 64
#define PROM_SERIAL_MAX_PATH 256
#define PROM_SERIAL_BAUD_DEFAULT 115200

typedef enum {
    PROM_SERIAL_OK = 0,
    PROM_SERIAL_ERR_OPEN = -1,
    PROM_SERIAL_ERR_CONFIG = -2,
    PROM_SERIAL_ERR_READ = -3,
    PROM_SERIAL_ERR_WRITE = -4,
    PROM_SERIAL_ERR_NOT_FOUND = -5,
    PROM_SERIAL_ERR_TIMEOUT = -6,
    PROM_SERIAL_ERR_NO_LIB = -7,
} prom_serial_err_t;

typedef enum {
    PROM_SERIAL_PARITY_NONE = 0,
    PROM_SERIAL_PARITY_ODD = 1,
    PROM_SERIAL_PARITY_EVEN = 2,
    PROM_SERIAL_PARITY_MARK = 3,
    PROM_SERIAL_PARITY_SPACE = 4,
} prom_serial_parity_t;

typedef enum {
    PROM_SERIAL_STOP_1 = 1,
    PROM_SERIAL_STOP_2 = 2,
} prom_serial_stop_bits_t;

typedef enum {
    PROM_SERIAL_FLOW_NONE = 0,
    PROM_SERIAL_FLOW_RTS_CTS = 1,
    PROM_SERIAL_FLOW_XON_XOFF = 2,
    PROM_SERIAL_FLOW_DTR_DSR = 3,
} prom_serial_flow_control_t;

typedef struct {
    char path[PROM_SERIAL_MAX_PATH];
    char description[128];
    uint32_t baud_rate;
    uint8_t data_bits;
    prom_serial_parity_t parity;
    prom_serial_stop_bits_t stop_bits;
    prom_serial_flow_control_t flow_control;
    bool is_open;
} prom_serial_port_info_t;

typedef struct {
    prom_serial_port_info_t ports[PROM_SERIAL_MAX_PORTS];
    size_t count;
    prom_serial_err_t error;
} prom_serial_port_list_t;

typedef struct {
    uint8_t *buffer;
    size_t length;
    size_t transferred;
    prom_serial_err_t error;
} prom_serial_transfer_result_t;

prom_serial_port_list_t prom_serial_list_ports(void);
void prom_serial_free_port_list(prom_serial_port_list_t *list);
prom_serial_err_t prom_serial_open(const char *path, uint32_t baud_rate);
prom_serial_err_t prom_serial_close(const char *path);
prom_serial_err_t prom_serial_configure(const char *path, uint8_t data_bits,
    prom_serial_parity_t parity, prom_serial_stop_bits_t stop_bits,
    prom_serial_flow_control_t flow_control);
prom_serial_transfer_result_t prom_serial_read(const char *path, uint8_t *buffer, size_t length, uint32_t timeout_ms);
prom_serial_transfer_result_t prom_serial_write(const char *path, const uint8_t *buffer, size_t length, uint32_t timeout_ms);
prom_serial_err_t prom_serial_set_baud(const char *path, uint32_t baud_rate);
prom_serial_err_t prom_serial_flush(const char *path);
prom_serial_err_t prom_serial_drain(const char *path);
bool prom_serial_is_open(const char *path);
const char *prom_serial_strerror(prom_serial_err_t err);

#ifdef __cplusplus
}
#endif

#endif /* PROMETHEUS_HAL_SERIAL_H */
