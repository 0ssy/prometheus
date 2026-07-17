#ifndef HAL_BINDINGS_H
#define HAL_BINDINGS_H

int hal_usb_probe(const char *target, char *out, size_t out_len);
int hal_serial_probe(const char *target, char *out, size_t out_len);
int hal_jtag_probe(const char *target, char *out, size_t out_len);

#endif
