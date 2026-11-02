# Pinned boot image packager

`mkbootimg.py` is an unmodified copy from Debian's `android-platform-tools`
34.0.5-12 source package, derived from the Android Open Source Project.
Its original copyright and Apache-2.0 notice remain in the file; the complete
license is in `LICENSE.mkbootimg`.

- [Versioned source](https://sources.debian.org/src/android-platform-tools/34.0.5-12/system/tools/mkbootimg/mkbootimg.py/)
- [Direct source file](https://sources.debian.org/data/main/a/android-platform-tools/34.0.5-12/system/tools/mkbootimg/mkbootimg.py)
- [Debian patch series](https://sources.debian.org/patches/android-platform-tools/34.0.5-12/), including removal of the optional GKI signing dependency.
- SHA-256: `b682574d42fd5c5cb852e7e76996b0e460808f10f47d81fc01e7f6db1697da4e`.

This version uses the Python standard library. Some distribution packages import
a missing `gki` module even when packing a legacy image. Keeping the exact
reviewed tool here makes the project's default build independent of that host
package defect. Mi 5 uses Android boot header version 0; GKI signing is not part
of its stock-LK boot flow.

`build-bootimg.sh` uses this copy by default. `MKBOOTIMG=/path/to/executable`
remains an explicit override and is checked before initramfs compilation.
Review source, license, hash, header-layout tests and actual image equivalence
when updating this dependency; do not replace it with an unpinned download.
