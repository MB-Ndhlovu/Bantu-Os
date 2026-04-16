# bantu_os/init/Makefile

CC = gcc
CFLAGS = -Wall -Wextra -Werror -pedantic -std=c11 -D_GNU_SOURCE
LDFLAGS =

TARGET = bantu-init
SRCS = init.c
OBJS = $(SRCS:.c=.o)

.PHONY: all clean install

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(TARGET) $(OBJS)

install: $(TARGET)
	install -m 0755 $(TARGET) /sbin/$(TARGET)
