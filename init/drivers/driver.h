/*
 * Bantu-OS Device Driver Framework
 * Layer 2: Character devices, block devices, virtual devices
 *
 * Design:
 *   All drivers implement a common init(), read(), write(), ioctl() interface.
 *   Registration is done via BANTU_DRIVER_REGISTER() macro at file scope.
 *   The kernel probes drivers by calling bantu_driver_init() for each entry.
 */

#ifndef BANTU_DRIVER_H
#define BANTU_DRIVER_H

#include <sys/types.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- Driver types ---- */
#define BANTU_DRV_CHAR     1   /* character device  */
#define BANTU_DRV_BLOCK   2   /* block device      */
#define BANTU_DRV_VIRTUAL 3   /* virtual / synthetic */

/* ---- Driver status ---- */
#define BANTU_DRV_OK       0
#define BANTU_DRV_ERR     -1
#define BANTU_DRV_BUSY    -2
#define BANTU_DRV_NOMEM   -3

/* ---- Open modes ---- */
#define BANTU_O_RDONLY   0
#define BANTU_O_WRONLY   1
#define BANTU_O_RDWR     2
#define BANTU_O_NONBLOCK 4

/* Forward declaration */
struct bantu_driver;

/* ---- Driver interface ---- */
typedef int (*bantu_drv_init_t)(struct bantu_driver *drv);
typedef void (*bantu_drv_shutdown_t)(struct bantu_driver *drv);
typedef int (*bantu_drv_open_t)(struct bantu_driver *drv, int mode);
typedef void (*bantu_drv_close_t)(struct bantu_driver *drv);
typedef ssize_t (*bantu_drv_read_t)(struct bantu_driver *drv, void *buf, size_t count, long offset);
typedef ssize_t (*bantu_drv_write_t)(struct bantu_driver *drv, const void *buf, size_t count, long offset);
typedef int (*bantu_drv_ioctl_t)(struct bantu_driver *drv, unsigned long cmd, void *arg);

/* ---- Driver descriptor ---- */
struct bantu_driver {
    const char *name;
    int type;            /* BANTU_DRV_* */
    int minor;           /* minor device number */
    int status;          /* current driver status */

    bantu_drv_init_t     init;
    bantu_drv_shutdown_t shutdown;
    bantu_drv_open_t     open;
    bantu_drv_close_t    close;
    bantu_drv_read_t     read;
    bantu_drv_write_t    write;
    bantu_drv_ioctl_t    ioctl;

    void *private_data;   /* driver-private data */
};

/* ---- Registration API ---- */
int  bantu_driver_register(struct bantu_driver *drv);
int  bantu_driver_unregister(const char *name);
struct bantu_driver *bantu_driver_find(const char *name);
int  bantu_driver_init_all(void);
void bantu_driver_shutdown_all(void);

/* ---- Built-in null / zero device ---- */
int bantu_null_init(void);

#ifdef __cplusplus
}
#endif

#endif /* BANTU_DRIVER_H */