/* Linker script for STM32F407VGT6 (ARM Cortex-M4F)
 * Flash: 1024 KiB at 0x08000000
 * SRAM:  128 KiB at 0x20000000
 * CCM:   64 KiB at 0x10000000
 */

ENTRY(Reset_Handler)

_estack = ORIGIN(RAM) + LENGTH(RAM); /* End of SRAM (Stack Top) */

_min_heap_size  = 0x400;  /* 1 KiB min heap */
_min_stack_size = 0x2000; /* 8 KiB min stack */

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
    CCM   (rwx) : ORIGIN = 0x10000000, LENGTH = 64K
}

SECTIONS
{
    /* Interrupt vector table at flash origin */
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } > FLASH

    /* Executable code */
    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame)
        KEEP (*(.init))
        KEEP (*(.fini))
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    /* Read-only data (constants, strings, lookup tables) */
    .rodata :
    {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
    } > FLASH

    /* ARM exception unwinding tables */
    .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } > FLASH
    .ARM : {
        __exidx_start = .;
        *(.ARM.exidx*)
        __exidx_end = .;
    } > FLASH

    /* Initialized data copied from Flash to SRAM at startup */
    _sidata = LOADADDR(.data);
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > RAM AT > FLASH

    /* Zero-initialized data (.bss) */
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        __bss_start__ = _sbss;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
        __bss_end__ = _ebss;
    } > RAM

    /* User heap and stack reservation */
    ._user_heap_stack :
    {
        . = ALIGN(8);
        PROVIDE ( end = . );
        PROVIDE ( _end = . );
        . = . + _min_heap_size;
        . = . + _min_stack_size;
        . = ALIGN(8);
    } > RAM

    /* Discard standard library debug info if stripping */
    /DISCARD/ :
    {
        libc.a ( * )
        libm.a ( * )
        libgcc.a ( * )
    }
}
