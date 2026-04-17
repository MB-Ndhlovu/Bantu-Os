# bantu_os/init/tests/Makefile

CC = gcc
CFLAGS = -Wall -Wextra -I.. -D_GNU_SOURCE
LDFLAGS =

TESTS = test_services

all: $(TESTS)

test_services: test_services.c ../services.c ../services.h
	$(CC) $(CFLAGS) -o $@ test_services.c ../services.c $(LDFLAGS)

clean:
	rm -f $(TESTS)

.PHONY: all clean