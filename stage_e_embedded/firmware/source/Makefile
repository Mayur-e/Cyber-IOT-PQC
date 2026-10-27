# Standalone Makefile for STM32F407 Cortex-M4 Embedded PQC Benchmark Harness
# Cross-compiler: ARM GNU Toolchain (arm-none-eabi-gcc)

CROSS_COMPILE ?= arm-none-eabi-
CC            := $(CROSS_COMPILE)gcc
OBJCOPY       := $(CROSS_COMPILE)objcopy
SIZE          := $(CROSS_COMPILE)size

TARGET        := firmware

SRCS          := main.c dwt_cycles.c stack_watermark.c uart_telemetry.c startup_stm32f407xx.c
OBJS          := $(SRCS:.c=.o)
LDSCRIPT      := stm32f407vg.ld

# Compiler and Linker Flags
MCU_FLAGS     := -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
OPT_FLAGS     := -O3 -g3
WARN_FLAGS    := -Wall -Wextra -Wshadow -Wno-unused-parameter

CFLAGS        := $(MCU_FLAGS) $(OPT_FLAGS) $(WARN_FLAGS) \
                 -ffunction-sections -fdata-sections \
                 -I.

LDFLAGS       := $(MCU_FLAGS) -T$(LDSCRIPT) \
                 -Wl,--gc-sections -Wl,-Map=$(TARGET).map \
                 --specs=nano.specs --specs=nosys.specs

.PHONY: all clean size

all: $(TARGET).elf $(TARGET).bin $(TARGET).hex size

$(TARGET).elf: $(OBJS) $(LDSCRIPT)
	@echo "  [LD]    $@"
	@$(CC) $(OBJS) $(LDFLAGS) -o $@

%.o: %.c
	@echo "  [CC]    $<"
	@$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).bin: $(TARGET).elf
	@echo "  [BIN]   $@"
	@$(OBJCOPY) -O binary $< $@

$(TARGET).hex: $(TARGET).elf
	@echo "  [HEX]   $@"
	@$(OBJCOPY) -O ihex $< $@

size: $(TARGET).elf
	@echo "=== Firmware Static Footprint (Flash & RAM) ==="
	@$(SIZE) -B $(TARGET).elf

clean:
	@rm -f $(OBJS) $(TARGET).elf $(TARGET).bin $(TARGET).hex $(TARGET).map
	@echo "Clean completed."
