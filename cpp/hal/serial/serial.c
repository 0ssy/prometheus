#include "serial.h"
#include <string.h>
#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <termios.h>
#include <unistd.h>
#include <fcntl.h>
#include <glob.h>
#include <sys/ioctl.h>
#endif

prom_serial_port_list_t prom_serial_list_ports(void) {
    prom_serial_port_list_t list;
    memset(&list, 0, sizeof(list));
    list.error = PROM_SERIAL_OK;

#ifdef _WIN32
    char ports[][6] = {"COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"};
    for (size_t i = 0; i < 8 && list.count < PROM_SERIAL_MAX_PORTS; i++) {
        snprintf(list.ports[list.count].path, sizeof(list.ports[list.count].path), "%s", ports[i]);
        snprintf(list.ports[list.count].description, sizeof(list.ports[list.count].description),
            "Serial Port %s", ports[i]);
        list.ports[list.count].baud_rate = PROM_SERIAL_BAUD_DEFAULT;
        list.ports[list.count].data_bits = 8;
        list.ports[list.count].parity = PROM_SERIAL_PARITY_NONE;
        list.ports[list.count].stop_bits = PROM_SERIAL_STOP_1;
        list.ports[list.count].flow_control = PROM_SERIAL_FLOW_NONE;
        list.count++;
    }
#else
    glob_t glob_result;
    if (glob("/dev/ttyUSB*", 0, NULL, &glob_result) == 0) {
        for (size_t i = 0; i < glob_result.gl_pathc && list.count < PROM_SERIAL_MAX_PORTS; i++) {
            snprintf(list.ports[list.count].path, sizeof(list.ports[list.count].path), "%s", glob_result.gl_pathv[i]);
            snprintf(list.ports[list.count].description, sizeof(list.ports[list.count].description),
                "USB Serial Device %s", glob_result.gl_pathv[i]);
            list.ports[list.count].baud_rate = PROM_SERIAL_BAUD_DEFAULT;
            list.ports[list.count].data_bits = 8;
            list.ports[list.count].parity = PROM_SERIAL_PARITY_NONE;
            list.ports[list.count].stop_bits = PROM_SERIAL_STOP_1;
            list.ports[list.count].flow_control = PROM_SERIAL_FLOW_NONE;
            list.count++;
        }
        globfree(&glob_result);
    }

    if (list.count == 0) {
        glob_t glob_result2;
        if (glob("/dev/ttyACM*", 0, NULL, &glob_result2) == 0) {
            for (size_t i = 0; i < glob_result2.gl_pathc && list.count < PROM_SERIAL_MAX_PORTS; i++) {
                snprintf(list.ports[list.count].path, sizeof(list.ports[list.count].path), "%s", glob_result2.gl_pathv[i]);
                snprintf(list.ports[list.count].description, sizeof(list.ports[list.count].description),
                    "ACM Serial Device %s", glob_result2.gl_pathv[i]);
                list.ports[list.count].baud_rate = PROM_SERIAL_BAUD_DEFAULT;
                list.ports[list.count].data_bits = 8;
                list.ports[list.count].parity = PROM_SERIAL_PARITY_NONE;
                list.ports[list.count].stop_bits = PROM_SERIAL_STOP_1;
                list.ports[list.count].flow_control = PROM_SERIAL_FLOW_NONE;
                list.count++;
            }
            globfree(&glob_result2);
        }
    }
#endif

    return list;
}

void prom_serial_free_port_list(prom_serial_port_list_t *list) {
    (void)list;
}

prom_serial_err_t prom_serial_open(const char *path, uint32_t baud_rate) {
#ifdef _WIN32
    HANDLE h = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) return PROM_SERIAL_ERR_OPEN;

    DCB dcb = {0};
    dcb.DCBlength = sizeof(DCB);
    dcb.BaudRate = baud_rate;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;

    if (!SetCommState(h, &dcb)) {
        CloseHandle(h);
        return PROM_SERIAL_ERR_CONFIG;
    }

    COMMTIMEOUTS timeouts = {0};
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutConstant = 50;
    timeouts.ReadTotalTimeoutMultiplier = 10;
    SetCommTimeouts(h, &timeouts);
    CloseHandle(h);
    return PROM_SERIAL_OK;
#else
    int fd = open(path, O_RDWR | O_NOCTTY | O_NDELAY);
    if (fd < 0) return PROM_SERIAL_ERR_OPEN;

    struct termios options;
    tcgetattr(fd, &options);
    speed_t speed = B115200;
    switch (baud_rate) {
        case 9600: speed = B9600; break;
        case 19200: speed = B19200; break;
        case 38400: speed = B38400; break;
        case 57600: speed = B57600; break;
        case 115200: speed = B115200; break;
        case 230400: speed = B230400; break;
        default: speed = B115200; break;
    }
    cfsetispeed(&options, speed);
    cfsetospeed(&options, speed);
    options.c_cflag |= (CLOCAL | CREAD);
    options.c_cflag &= ~CSIZE;
    options.c_cflag |= CS8;
    options.c_cflag &= ~PARENB;
    options.c_cflag &= ~CSTOPB;
    options.c_cflag &= ~CRTSCTS;
    tcsetattr(fd, TCSANOW, &options);
    close(fd);
    return PROM_SERIAL_OK;
#endif
}

prom_serial_err_t prom_serial_close(const char *path) {
    (void)path;
    return PROM_SERIAL_OK;
}

prom_serial_err_t prom_serial_configure(const char *path, uint8_t data_bits,
    prom_serial_parity_t parity, prom_serial_stop_bits_t stop_bits,
    prom_serial_flow_control_t flow_control) {
    (void)path;
    (void)data_bits;
    (void)parity;
    (void)stop_bits;
    (void)flow_control;
    return PROM_SERIAL_OK;
}

prom_serial_transfer_result_t prom_serial_read(const char *path, uint8_t *buffer, size_t length, uint32_t timeout_ms) {
    prom_serial_transfer_result_t result;
    memset(&result, 0, sizeof(result));
    (void)path;
    (void)buffer;
    (void)length;
    (void)timeout_ms;
    result.error = PROM_SERIAL_ERR_READ;
    return result;
}

prom_serial_transfer_result_t prom_serial_write(const char *path, const uint8_t *buffer, size_t length, uint32_t timeout_ms) {
    prom_serial_transfer_result_t result;
    memset(&result, 0, sizeof(result));
    (void)path;
    (void)buffer;
    (void)length;
    (void)timeout_ms;
    result.error = PROM_SERIAL_ERR_WRITE;
    return result;
}

prom_serial_err_t prom_serial_set_baud(const char *path, uint32_t baud_rate) {
    return prom_serial_open(path, baud_rate);
}

prom_serial_err_t prom_serial_flush(const char *path) {
    (void)path;
    return PROM_SERIAL_OK;
}

prom_serial_err_t prom_serial_drain(const char *path) {
    (void)path;
    return PROM_SERIAL_OK;
}

bool prom_serial_is_open(const char *path) {
    (void)path;
    return false;
}

const char *prom_serial_strerror(prom_serial_err_t err) {
    switch (err) {
        case PROM_SERIAL_OK: return "OK";
        case PROM_SERIAL_ERR_OPEN: return "open failed";
        case PROM_SERIAL_ERR_CONFIG: return "configuration failed";
        case PROM_SERIAL_ERR_READ: return "read failed";
        case PROM_SERIAL_ERR_WRITE: return "write failed";
        case PROM_SERIAL_ERR_NOT_FOUND: return "port not found";
        case PROM_SERIAL_ERR_TIMEOUT: return "timeout";
        case PROM_SERIAL_ERR_NO_LIB: return "native library not available";
        default: return "unknown error";
    }
}
