#include "stack_watermark.h"

static volatile uint32_t *g_stack_base = NULL;
static size_t g_stack_size_words = 0;
static uint32_t *g_stack_top = NULL;

void stack_watermark_init(uint32_t *stack_base, size_t stack_size) {
    g_stack_base = stack_base;
    g_stack_size_words = stack_size / sizeof(uint32_t);
    g_stack_top = stack_base + g_stack_size_words;
}

void stack_watermark_paint(void) {
    if (g_stack_base == NULL || g_stack_size_words == 0) {
        return;
    }

    /* Determine current stack position */
#if defined(__arm__)
    register uint32_t *current_sp __asm__("sp");
#else
    /* Mock stack pointer for host testing */
    uint32_t dummy = 0;
    uint32_t *current_sp = &dummy;
#endif

    /* Paint downwards from just below current SP down to stack base with safety margin */
    volatile uint32_t *p = current_sp - 16; /* Leave margin for watermark paint call itself */
    if (p > g_stack_top) {
        p = g_stack_top - 1;
    }

    while (p >= g_stack_base) {
        *p = STACK_CANARY_WORD;
        p--;
    }
}

size_t stack_watermark_measure(void) {
    if (g_stack_base == NULL || g_stack_size_words == 0) {
        return 0;
    }

    /* Scan from stack base (lowest address) upward to find first corrupted canary */
    volatile uint32_t *p = g_stack_base;
    while (p < g_stack_top && *p == STACK_CANARY_WORD) {
        p++;
    }

    /* Peak stack usage is the distance from stack top down to lowest overwritten word */
    size_t unused_words = (size_t)(p - g_stack_base);
    size_t used_words = g_stack_size_words - unused_words;

    return used_words * sizeof(uint32_t);
}
