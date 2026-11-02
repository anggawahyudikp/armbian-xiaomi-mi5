// SPDX-License-Identifier: MIT
// Gemini early userspace. Never deploy files to userdata from the initramfs.
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef GEMINI_DIAGNOSTIC
#define GEMINI_DIAGNOSTIC 0
#endif

static void mkdir_checked(const char *path)
{
	if (mkdir(path, 0755) && errno != EEXIST) {
		perror(path);
		for (;;) pause();
	}
}

static int read_text(const char *path, char *buf, size_t size)
{
	int fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0) return -1;
	ssize_t n = read(fd, buf, size - 1);
	close(fd);
	if (n < 0) return -1;
	buf[n] = '\0';
	return 0;
}

static void readonly_disks(void)
{
	DIR *dir = opendir("/sys/class/block");
	struct dirent *entry;
	if (!dir) return;
	while ((entry = readdir(dir))) {
		char path[512];
		if (strncmp(entry->d_name, "sd", 2) &&
		    strncmp(entry->d_name, "mmcblk", 6)) continue;
		snprintf(path, sizeof(path), "/dev/%s", entry->d_name);
		int fd = open(path, O_RDONLY | O_CLOEXEC), ro = 1;
		if (fd >= 0) {
			if (ioctl(fd, BLKROSET, &ro)) perror(path);
			close(fd);
		}
	}
	closedir(dir);
}

static void console_shell(const char *reason)
{
	// No filesystem is mounted here. Protect detected internal block nodes
	// against accidental writes during manual inspection in the rescue shell.
	readonly_disks();
	for (;;) {
		pid_t child = fork();
		if (!child) {
			setsid();
			// Opening ttyGS0 can block until the laptop opens its ACM port.
			int fd = open("/dev/ttyGS0", O_RDWR);
			if (fd < 0) _exit(1);
			ioctl(fd, TIOCSCTTY, 0);
			for (int i = 0; i < 3; i++) dup2(fd, i);
			if (fd > 2) close(fd);
			dprintf(1, "\nGemini %s\n%s\nInternal filesystems are NOT mounted.\n"
			        "Use gemini-diagnostics for a hardware summary.\n",
			        GEMINI_DIAGNOSTIC ? "diagnostic" : "rescue", reason);
			setenv("PATH", "/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
			setenv("HOME", "/root", 1);
			setenv("TERM", "vt100", 1);
			execl("/bin/busybox", "sh", "-i", NULL);
			_exit(127);
		}
		if (child > 0) while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {}
		sleep(1);
	}
}

static int find_userdata(char *dev, size_t size)
{
	for (int tick = 0; tick < 240; tick++) {
		DIR *dir = opendir("/sys/class/block");
		struct dirent *entry;
		if (dir) {
			while ((entry = readdir(dir))) {
				char path[512], info[2048];
				snprintf(path, sizeof(path), "/sys/class/block/%s/uevent", entry->d_name);
				if (read_text(path, info, sizeof(info))) continue;
				// Match a whole line, not userdata_backup or a fixed sda number.
				if (!strstr(info, "\nPARTNAME=userdata\n")) continue;
				snprintf(dev, size, "/dev/%s", entry->d_name);
				struct stat st;
				if (!stat(dev, &st) && S_ISBLK(st.st_mode)) {
					closedir(dir);
					return 0;
				}
			}
			closedir(dir);
		}
		usleep(250000);
	}
	return -1;
}

int main(void)
{
	if (getpid() != 1) {
		fputs("This program must run as init (PID 1).\n", stderr);
		return 1;
	}
	mkdir_checked("/proc"); mkdir_checked("/sys"); mkdir_checked("/dev");
	if (mount("proc", "/proc", "proc", 0, NULL) ||
	    mount("sysfs", "/sys", "sysfs", 0, NULL) ||
	    mount("devtmpfs", "/dev", "devtmpfs", 0, NULL)) {
		perror("early mounts");
		for (;;) pause();
	}
	int fd = open("/dev/console", O_RDWR);
	if (fd >= 0) {
		for (int i = 0; i < 3; i++) dup2(fd, i);
		if (fd > 2) close(fd);
	}
	if (GEMINI_DIAGNOSTIC) {
		// Wait for UFS probe, then offer an entirely RAM-resident environment.
		sleep(10);
		console_shell("No production rootfs will be selected or modified.");
	}

	char rootdev[512], marker[128];
	if (find_userdata(rootdev, sizeof(rootdev))) console_shell("userdata not found");
	mkdir_checked("/newroot");
	// noload prevents ext4 journal replay from writing to an unverified volume.
	if (mount(rootdev, "/newroot", "ext4", MS_RDONLY | MS_NOATIME, "noload"))
		console_shell("userdata is not a mountable ext4 rootfs; left untouched");
	int valid = !read_text("/newroot/etc/gemini-rootfs", marker, sizeof(marker)) &&
	            !strcmp(marker, "gemini-rootfs-v1\n") &&
	            // /sbin/init may be an absolute symlink. Before chroot, following
	            // that link would incorrectly resolve inside the initramfs.
	            !access("/newroot/usr/lib/systemd/systemd", X_OK);
	if (umount("/newroot")) console_shell("cannot unmount rootfs validation mount");
	if (!valid) console_shell("userdata is not an identified Gemini rootfs; left untouched");
	// Leave the identified root read-only for systemd-fsck-root.service.
	// Mounting writable here skips its ConditionPathIsReadWrite=!/ guard,
	// allowing damaged metadata to reach multi-user services without fsck.
	// Unlike the unverified noload probe, this mount permits journal replay.
	// systemd checks root before systemd-remount-fs makes it writable via fstab.
	if (mount(rootdev, "/newroot", "ext4", MS_RDONLY | MS_NOATIME, NULL))
		console_shell("cannot mount validated rootfs read-only for filesystem check");

	mkdir_checked("/newroot/proc"); mkdir_checked("/newroot/sys"); mkdir_checked("/newroot/dev");
	if (mount("/proc", "/newroot/proc", NULL, MS_MOVE, NULL) ||
	    mount("/sys", "/newroot/sys", NULL, MS_MOVE, NULL) ||
	    mount("/dev", "/newroot/dev", NULL, MS_MOVE, NULL)) {
		perror("move virtual filesystems");
		for (;;) pause();
	}
	// BusyBox switch_root frees the initramfs before execing systemd.
	execl("/bin/busybox", "busybox", "switch_root", "/newroot", "/sbin/init", NULL);
	perror("switch_root");
	for (;;) pause();
}
