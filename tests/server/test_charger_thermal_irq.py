"""Exercise the real thermal IRQ callback with live/cleared/error status."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / 'overlays/linux/drivers/power/supply/qcom-smbchg.c'
HEADER = DRIVER.with_suffix('.h')


class ChargerThermalIRQTest(unittest.TestCase):
    def test_only_cleared_alarm_avoids_shutdown_and_read_errors_fail_closed(self):
        source = DRIVER.read_text()
        start = source.index('static irqreturn_t smbchg_handle_temp_shutdown(')
        callback = source[start:source.index('\n}\n', start) + 3]
        constants = '\n'.join(re.findall(
            r'^#define (?:SMBCHG_MISC_RT_STS|MISC_TEMP_SHUTDOWN_BIT)\b.*$',
            HEADER.read_text(), re.M))
        harness = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#define BIT(n) (1u << (n))
#define dev_info_ratelimited(...) ((void)0)
#define dev_err(...) ((void)0)
#define dev_crit(...) ((void)0)
#define IRQ_HANDLED 1
typedef unsigned int u32;
typedef int irqreturn_t;
CONSTANTS
struct smbchg_chip { void *dev, *regmap, *usb_psy; unsigned int base; };
static struct smbchg_chip chip = { (void *)1, (void *)2, (void *)3, 0x1000 };
static int read_error;
static unsigned int live_status;
static char actions[16];
static unsigned int count;
static void action(char value) { assert(count < sizeof(actions)-1); actions[count++] = value; }
static int regmap_read(void *map, unsigned int reg, u32 *status) {
    assert(map == chip.regmap);
    assert(reg == 0x1610); /* live level, never the latched IRQ register */
    action('R'); *status = live_status; return read_error;
}
static void hw_protection_trigger(const char *reason, int delay) {
    assert(strcmp(reason, "Charger thermal emergency") == 0);
    assert(delay == 100); action('H');
}
static int smbchg_charging_enable(struct smbchg_chip *c, bool enable) {
    assert(c == &chip && !enable); action('C'); return 0;
}
static int smbchg_usb_enable(struct smbchg_chip *c, bool enable) {
    assert(c == &chip && !enable); action('U'); return 0;
}
static void power_supply_changed(void *psy) { assert(psy == chip.usb_psy); action('P'); }
CALLBACK
static void check(int error, unsigned int status, const char *expected) {
    memset(actions, 0, sizeof(actions)); count = 0;
    read_error = error; live_status = status;
    assert(smbchg_handle_temp_shutdown(42, &chip) == IRQ_HANDLED);
    assert(strcmp(actions, expected) == 0);
}
int main(void) {
    /* Unrelated status bits must not suppress an active thermal alarm. */
    for (unsigned int status = 0; status < 256; status++)
        check(0, status, status & BIT(1) ? "RHCUP" : "RP");
    const int errors[] = { -5, -19, -110 };
    for (unsigned int i = 0; i < sizeof(errors)/sizeof(errors[0]); i++) {
        check(errors[i], 0, "RHCUP");
        check(errors[i], BIT(1), "RHCUP");
    }
}
'''.replace('CONSTANTS', constants).replace('CALLBACK', callback)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'test.c').write_text(harness)
            subprocess.run(['cc', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', str(path / 'test.c'),
                            '-o', str(path / 'test')], check=True)
            subprocess.run([str(path / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
