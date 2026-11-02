# Third-party notices

Project code is provided under the GNU General Public License version 2; see
LICENSE. Preserve notices and licenses already present in individual files.

- Linux kernel sources are obtained separately from the pinned upstream source.
  Project kernel overlays retain their existing upstream copyright notices and
  SPDX identifiers. See overlays/README.md and scripts/setup-kernel.sh.
- The Armbian build framework is obtained separately at the revision in
  armbian/framework-revision. Its own licensing applies to that source.
- The unmodified pinned AOSP/Debian mkbootimg.py retains its Apache-2.0 notice.
  Its full license is scripts/vendor/LICENSE.mkbootimg; provenance and source
  links are documented in scripts/vendor/README.md.
- Firmware binaries are local inputs, not covered by the project-code license
  and not distributed here. See docs/firmware-inputs.md.
- Third-party teardown photos and datasheets are linked from the UART reference
  guide instead of being redistributed under the project's license.
