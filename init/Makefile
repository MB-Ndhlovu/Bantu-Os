CC = gcc
CFLAGS = -Wall -Wextra -pedantic -std=c11 -O2
TARGET = bantu_init
SRC = init.c

.PHONY: all clean install check

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(TARGET)

install: $(TARGET)
	cp $(TARGET) /sbin/bantu_init
	chmod +x /sbin/bantu_init

check: $(TARGET)
	@echo "Running basic checks..."
	@if [ ! -x $(TARGET) ]; then echo "FAIL: Binary not built"; exit 1; fi
	@echo "Binary size:"
	@ls -lh $(TARGET)
	@echo "Symbol table:"
	@nm -s $(TARGET) | head -20
	@echo "OK: $(TARGET) built successfully"