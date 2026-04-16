# Bantu-OS Init Tests Makefile

CC = gcc
CFLAGS = -Wall -Wextra -g -DTEST_BUILD -I..
LDFLAGS =

.PHONY: all clean test run-tests

all: test_services

test_services: test_services.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

run-tests: test_services
	./test_services

clean:
	rm -f test_services
