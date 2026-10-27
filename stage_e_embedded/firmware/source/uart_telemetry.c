#include "uart_telemetry.h"
#include <stdio.h>
#include <string.h>

#if defined(__arm__) && (defined(__ARM_ARCH_7EM__) || defined(__ARM_ARCH_7M__))
/* STM32F4 USART2 direct register definitions */
#define RCC_AHB1ENR  (*((volatile uint32_t *)0x40023830UL))
#define RCC_APB1ENR  (*((volatile uint32_t *)0x40023840UL))

#define GPIOA_MODER  (*((volatile uint32_t *)0x40020000UL))
#define GPIOA_AFRL   (*((volatile uint32_t *)0x40020020UL))

#define USART2_SR    (*((volatile uint32_t *)0x40004400UL))
#define USART2_DR    (*((volatile uint32_t *)0x40004404UL))
#define USART2_BRR   (*((volatile uint32_t *)0x40004408UL))
#define USART2_CR1   (*((volatile uint32_t *)0x4000440CUL))

#define USART_SR_TXE (1UL << 7)
#define USART_CR1_UE (1UL << 13)
#define USART_CR1_TE (1UL << 3)
#define USART_CR1_RE (1UL << 2)

void uart_telemetry_init(uint32_t baud_rate) {
    /* Enable GPIOA (bit 0) and USART2 (bit 17) peripheral clocks */
    RCC_AHB1ENR |= (1UL << 0);
    RCC_APB1ENR |= (1UL << 17);

    /* Configure PA2 (TX) and PA3 (RX) as Alternate Function (MODER = 10b) */
    GPIOA_MODER &= ~((3UL << (2 * 2)) | (3UL << (3 * 2)));
    GPIOA_MODER |=  ((2UL << (2 * 2)) | (2UL << (3 * 2)));

    /* Set AF7 (USART2) for PA2 and PA3 in AFRL */
    GPIOA_AFRL &= ~((0xFUL << (2 * 4)) | (0xFUL << (3 * 4)));
    GPIOA_AFRL |=  ((7UL << (2 * 4)) | (7UL << (3 * 4)));

    /* Assume APB1 clock is 42 MHz (typical for 168 MHz sysclk) or 12 MHz (for 24 MHz sysclk).
     * For 115200 at 42 MHz: 42000000 / 115200 = 364.58 -> BRR = 0x16D */
    if (baud_rate == 115200) {
        USART2_BRR = 0x016D; /* 42 MHz / 115200 */
    } else {
        USART2_BRR = 0x0445; /* 38400 baud default */
    }

    /* Enable USART, Transmitter, and Receiver */
    USART2_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

void uart_send_byte(uint8_t byte) {
    while (!(USART2_SR & USART_SR_TXE));
    USART2_DR = byte;
}

#else
/* Host / Semihosting fallback */
void uart_telemetry_init(uint32_t baud_rate) {
    (void)baud_rate;
}

void uart_send_byte(uint8_t byte) {
    putchar(byte);
}
#endif

void uart_send_str(const char *str) {
    while (*str) {
        uart_send_byte((uint8_t)*str);
        str++;
    }
}

void uart_emit_csv_header(void) {
    uart_send_str("run_id,device,board,mcu,algorithm,operation,implementation,"
                  "library_name,library_version,compiler,opt_flags,clock_hz,"
                  "measurement_method,trial,cycles,elapsed_us,status,valid,warmup,stack_bytes,notes\r\n");
}

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
) {
    char buf[512];
    snprintf(buf, sizeof(buf),
        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%lu,%s,%lu,%lu,%.3f,%s,%s,%s,%lu,%s\r\n",
        run_id ? run_id : "unknown",
        device ? device : "unknown",
        board ? board : "unknown",
        mcu ? mcu : "unknown",
        algorithm ? algorithm : "unknown",
        operation ? operation : "unknown",
        implementation ? implementation : "unknown",
        library_name ? library_name : "unknown",
        library_version ? library_version : "unknown",
        compiler_info ? compiler_info : "gcc",
        opt_flags ? opt_flags : "-O3",
        (unsigned long)clock_hz,
        measurement_method ? measurement_method : "dwt_cyccnt",
        (unsigned long)trial,
        (unsigned long)cycles,
        elapsed_us,
        status ? status : "success",
        valid ? "true" : "false",
        warmup ? "true" : "false",
        (unsigned long)stack_bytes,
        notes ? notes : ""
    );
    uart_send_str(buf);
}
