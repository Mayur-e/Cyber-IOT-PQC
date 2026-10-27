#ifndef UART_TELEMETRY_H
#define UART_TELEMETRY_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize USART hardware at specified baud rate (e.g. 115200 or 38400).
 * Configures GPIO pins, enables peripheral clocks, configures 8N1 framing.
 */
void uart_telemetry_init(uint32_t baud_rate);

/**
 * @brief Send a null-terminated string over UART.
 */
void uart_send_str(const char *str);

/**
 * @brief Send a raw byte over UART.
 */
void uart_send_byte(uint8_t byte);

/**
 * @brief Emit CSV header matching Stage E schema.
 */
void uart_emit_csv_header(void);

/**
 * @brief Emit a structured CSV observation record over UART.
 */
void uart_emit_record(
    const char *run_id,
    const char *device,
    const char *board,
    const char *mcu,
    const char *algorithm,
    const char *operation,
    const char *implementation,
    const char *library_name,
    const char *library_version,
    const char *compiler_info,
    const char *opt_flags,
    uint32_t clock_hz,
    const char *measurement_method,
    uint32_t trial,
    uint32_t cycles,
    double elapsed_us,
    const char *status,
    bool valid,
    bool warmup,
    size_t stack_bytes,
    const char *notes
);

#ifdef __cplusplus
}
#endif

#endif /* UART_TELEMETRY_H */
