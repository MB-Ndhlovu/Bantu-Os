# Bantu-OS Init System Makefile

CC = gcc
CFLAGS = -Wall -Wextra -g
LDFLAGS = -static

INIT_BINARY = bantu-init

.PHONY: all clean test install

all: $(INIT_BINARY)

$(INIT_BINARY): init.c services.c services.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ init.c services.c
	@echo \"Built: $@\"

clean:
	rm -f $(INIT_BINARY)

test:
	cd tests && $(MAKE) run-tests

install: $(INIT_BINARY)
	install -D -m 755 $(INIT_BINARY) ../initramfs/bantu-init
	@echo \"Installed to initramfs/bantu-init\"
