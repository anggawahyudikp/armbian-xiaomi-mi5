# Docker workloads

The generic image supplies the Armbian base system and container-capable kernel.
Docker was installed separately on the test phone; it is not preinstalled in
the generic rootfs. Configure Wi-Fi and complete first login before installing
applications.

The native checks used Debian Bookworm's Docker package with ARM64 containers,
overlay2 and cgroup v2. Debian provides an [ARM64 docker.io package](https://packages.debian.org/bookworm/docker.io).
This describes measured device compatibility, not official Mi 5 support from
Debian, Docker or Armbian.

```sh
sudo apt update
sudo apt install docker.io
sudo systemctl enable --now docker
sudo docker info
sudo docker run --rm hello-world
```

The last command needs registry access to download an image. Select images
that provide `linux/arm64`; an image available only for `linux/amd64` cannot
run natively on this phone. Use `sudo` for the examples. If choosing permanent
non-root Docker access, understand the [Docker group's privileges](https://docs.docker.com/engine/install/linux-postinstall/).

For a persistent application, keep its Compose file and data paths, configure
its restart policy and verify HTTP or another real application request after
reboot. Stop the application or use its database's consistent export before
backing up data. Restore into a separate location and verify the result before
overwriting live data.

The current acceptance fixture on port 18080 is a small HTTP counter with
persistent data. Its restart and backup/restore checks do not establish the
behavior of every application. It is not shipped in the generic image. The
[stability acceptance report](stability-acceptance-2026-10-31.md) records its
actual runtime results and remaining release gates.
