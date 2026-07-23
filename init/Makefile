# Bantu-OS Init System Makefile

CC = gcc
CFLAGS = -Wall -Wextra -Werror -std=c11 -g
LDFLAGS = -static

INIT_BINARY = bantu-init

.PHONY: all clean test install

all: $(INIT_BINARY)

$(INIT_BINARY): init.c services.c services.h registry_socket.c registry_socket.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ init.c services.c registry_socket.c
	@echo \"Built: $@\"

test:
	$(MAKE) -C tests clean all
	./tests/test_services
	$(MAKE) -C tests clean

clean:
	rm -f $(INIT_BINARY)

install: $(INIT_BINARY)
	install -D -m 755 $(INIT_BINARY) ../initramfs/bantu-init
	@echo \"Installed to initramfs/bantu-init\"
