#ifndef STACK_WATERMARK_H
#define STACK_WATERMARK_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define STACK_CANARY_WORD 0x5A5A5A5AUL

/**
 * @brief Initialize stack watermarking boundaries.
 * @param stack_base Pointer to the bottom of the stack region (lowest address).
 * @param stack_size Total size of the stack area in bytes.
 */
void stack_watermark_init(uint32_t *stack_base, size_t stack_size);

/**
 * @brief Paint the stack region between current stack pointer and stack base with CANARY.
 * Must be called immediately before executing the target cryptographic function.
 */
void stack_watermark_paint(void);

/**
 * @brief Measure the peak stack usage in bytes by scanning for the lowest modified canary word.
 * @return size_t Peak stack consumption in bytes.
 */
size_t stack_watermark_measure(void);

#ifdef __cplusplus
}
#endif

#endif /* STACK_WATERMARK_H */
