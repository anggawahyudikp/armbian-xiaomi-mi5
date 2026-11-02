// Exercise the real init state machine with simulated syscalls; no disks mounted.
#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int scenario, root_mounts, writable_mounts, unmounted, disk_ro, switched, iter;
static jmp_buf done;
static int test_mount(const char *src, const char *dst, const char *type,
                      unsigned long flags, const void *data)
{
    (void)src;
    if (!strcmp(dst, "/newroot")) {
        root_mounts++;
        assert(!strcmp(type, "ext4"));
        if (!(flags & MS_RDONLY)) writable_mounts++;
        assert(flags & MS_RDONLY);
        if (root_mounts == 1) {
            assert(data && !strcmp(data, "noload"));
        } else {
            // Only an identified root may replay its journal. Keep it read-only
            // so systemd-fsck-root runs before the fstab remount to writable.
            assert(scenario == 2 && unmounted == 1 && data == NULL);
        }
        if (scenario == 0) { errno = EINVAL; return -1; }
    }
    return 0;
}
static int test_umount(const char *path) { assert(!strcmp(path, "/newroot")); unmounted++; return 0; }
static int test_open(const char *path, int flags, ...)
{
    assert(!(flags & (O_CREAT | O_TRUNC | O_WRONLY)));
    if (!strcmp(path, "/dev/console")) return -1;
    if (!strcmp(path, "/sys/class/block/sda14/uevent")) return 101;
    if (!strcmp(path, "/newroot/etc/gemini-rootfs")) return 102;
    if (!strcmp(path, "/dev/sda14")) return 103;
    if (!strcmp(path, "/dev/ttyGS0")) return 104;
    assert(!"Unexpected open"); return -1;
}
static ssize_t test_read(int fd, void *buf, size_t size)
{
    const char *text = fd == 101 ? "DEVNAME=sda14\nPARTNAME=userdata\n" :
                       scenario == 2 ? "gemini-rootfs-v1\n" : "android-data\n";
    assert(fd == 101 || fd == 102);
    assert(strlen(text) <= size);
    memcpy(buf, text, strlen(text)); return strlen(text);
}
static DIR *test_opendir(const char *path) { assert(!strcmp(path, "/sys/class/block")); iter = 0; return (DIR *)1; }
static __attribute__((noinline)) struct dirent *test_readdir(DIR *dir)
{
    (void)dir;
    static struct dirent entry;
    if (iter++) return NULL;
    strcpy(entry.d_name, "sda14"); return &entry;
}
static int test_stat(const char *path, struct stat *st) { assert(!strcmp(path, "/dev/sda14")); st->st_mode = S_IFBLK | 0600; return 0; }
static int test_ioctl(int fd, unsigned long request, ...)
{
    if (request == BLKROSET) { assert(fd == 103); disk_ro++; }
    else assert(request == TIOCSCTTY);
    return 0;
}
static int test_execl(const char *path, const char *arg, ...)
{
    assert(!strcmp(path, "/bin/busybox"));
    switched = !strcmp(arg, "busybox");
    longjmp(done, 1);
}
static int test_mkdir(const char *path, mode_t mode) { (void)path; (void)mode; return 0; }
static int test_access(const char *path, int mode) { assert(!strcmp(path, "/newroot/usr/lib/systemd/systemd")); assert(mode == X_OK); return 0; }
static int test_close(int fd) { (void)fd; return 0; }
static int test_closedir(DIR *dir) { (void)dir; return 0; }
static int test_dup2(int oldfd, int newfd) { (void)oldfd; return newfd; }
static unsigned test_sleep(unsigned n) { (void)n; return 0; }
static int test_usleep(useconds_t n) { (void)n; return 0; }
static pid_t test_getpid(void) { return 1; }
static pid_t test_fork(void) { return 0; }
static pid_t test_setsid(void) { return 1; }

#define mount test_mount
#define umount test_umount
#define open test_open
#define read test_read
#define opendir test_opendir
#define readdir test_readdir
#define stat(path, st) test_stat(path, st)
#define ioctl test_ioctl
#define execl test_execl
#define mkdir test_mkdir
#define access test_access
#define close test_close
#define closedir test_closedir
#define dup2 test_dup2
#define sleep test_sleep
#define usleep test_usleep
#define getpid test_getpid
#define fork test_fork
#define setsid test_setsid
#define main gemini_init_main
#include "../../initramfs/init.c"
#undef main

int main(void)
{
    for (scenario = 0; scenario < 3; scenario++) {
        root_mounts = writable_mounts = unmounted = disk_ro = switched = 0;
        if (!setjmp(done)) gemini_init_main();
        if (GEMINI_DIAGNOSTIC) {
            assert(root_mounts == 0 && writable_mounts == 0 && disk_ro == 1 && !switched);
        } else if (scenario == 0) {
            assert(root_mounts == 1 && writable_mounts == 0 && disk_ro == 1 && !switched);
        } else if (scenario == 1) {
            assert(root_mounts == 1 && writable_mounts == 0 && unmounted == 1 && disk_ro == 1 && !switched);
        } else {
            assert(root_mounts == 2 && writable_mounts == 0 && switched);
        }
    }
    printf("PASS: %s init protects Android/F2FS and unmarked ext4; validated production rootfs stays read-only until systemd fsck/remount\n",
           GEMINI_DIAGNOSTIC ? "diagnostic" : "production");
    return 0;
}
