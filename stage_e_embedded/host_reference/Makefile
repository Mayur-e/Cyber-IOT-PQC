CC ?= gcc
CFLAGS ?= -O3 -Wall -Wextra -std=c11 -I./include -I/root/_oqs/include
LDFLAGS ?= -L/root/_oqs/lib -Wl,-rpath,/root/_oqs/lib
LDLIBS ?= -loqs -lcrypto -lm

SRC_DIR = src
TEST_DIR = tests
BIN_DIR = bin

TARGET_BENCH = $(BIN_DIR)/benchmark_native
TARGET_TEST = $(BIN_DIR)/test_native

all: $(TARGET_BENCH) $(TARGET_TEST)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(TARGET_BENCH): $(SRC_DIR)/benchmark_native.c $(SRC_DIR)/stats.c | $(BIN_DIR)
	$(CC) $(CFLAGS) $^ $(LDFLAGS) $(LDLIBS) -o $@

$(TARGET_TEST): $(TEST_DIR)/test_native.c $(SRC_DIR)/stats.c | $(BIN_DIR)
	$(CC) $(CFLAGS) $^ $(LDFLAGS) $(LDLIBS) -o $@

test: $(TARGET_TEST)
	./$(TARGET_TEST)

clean:
	rm -rf $(BIN_DIR)

.PHONY: all test clean
