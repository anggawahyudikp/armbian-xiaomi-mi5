#!/usr/bin/env python3
"""Run the actual DWC3 current callback against mocked power supplies."""
import ast
import pathlib
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ChargerPolicyTest(unittest.TestCase):
    def test_charger_ports_keep_aicl_and_sdp_keeps_host_limits(self):
        # Apply the production operation to a pinned, unmodified upstream excerpt.
        # Running that operation avoids duplicating charger policy in the test.
        script = (ROOT/'scripts/apply-overlays.sh').read_text()
        body = script.split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]
        module = ast.parse(body)
        helper = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'once')
        patch = next(n for n in module.body if isinstance(n, ast.Expr)
                     and isinstance(n.value, ast.Call)
                     and isinstance(n.value.func, ast.Name) and n.value.func.id == 'once'
                     and isinstance(n.value.args[0], ast.BinOp)
                     and isinstance(n.value.args[0].right, ast.Constant)
                     and n.value.args[0].right.value == 'drivers/usb/dwc3/core.c')
        code = compile(ast.Module(body=[helper, patch], type_ignores=[]), str(ROOT/'scripts/apply-overlays.sh'), 'exec')
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            target = tree/'drivers/usb/dwc3/core.c'
            target.parent.mkdir(parents=True)
            target.write_text((ROOT/'tests/server/fixtures/dwc3-vbus-draw-upstream.c').read_text())
            context = {'pathlib': pathlib, 'src': tree}
            exec(code, context)
            source = target.read_text()
            exec(code, context)
            self.assertEqual(target.read_text(), source, 'Production patch must be idempotent')
        start = source.index('static void dwc3_vbus_draw_work(')
        end = source.index('\n}\n', start) + 3
        callback = source[start:end]
        harness = r'''
#include <assert.h>
#include <stddef.h>
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define dev_dbg(...) ((void)0)
enum { POWER_SUPPLY_PROP_USB_TYPE, POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT };
enum { POWER_SUPPLY_USB_TYPE_UNKNOWN, POWER_SUPPLY_USB_TYPE_SDP,
       POWER_SUPPLY_USB_TYPE_DCP, POWER_SUPPLY_USB_TYPE_CDP };
struct work_struct { int unused; };
union power_supply_propval { int intval; };
struct dwc3 { struct work_struct vbus_draw_work; int current_limit; void *usb_psy; };
static int type, read_error, writes, written;
static int power_supply_get_property(void *psy, int property,
                                      union power_supply_propval *val) {
    (void)psy; assert(property == POWER_SUPPLY_PROP_USB_TYPE);
    val->intval = type; return read_error;
}
static int power_supply_set_property(void *psy, int property,
                                      union power_supply_propval *val) {
    (void)psy; assert(property == POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT);
    writes++; written = val->intval; return 0;
}
CALLBACK
int main(void) {
    const int limits[] = { 0, 2, 100, 500 };
    struct dwc3 dwc = {0};
    for (type = POWER_SUPPLY_USB_TYPE_UNKNOWN; type <= POWER_SUPPLY_USB_TYPE_CDP; type++)
        for (unsigned int i = 0; i < sizeof(limits)/sizeof(limits[0]); i++) {
            dwc.current_limit = limits[i]; writes = 0;
            dwc3_vbus_draw_work(&dwc.vbus_draw_work);
            if (type == POWER_SUPPLY_USB_TYPE_DCP || type == POWER_SUPPLY_USB_TYPE_CDP)
                assert(writes == 0);
            else {
                assert(writes == 1);
                assert(written == limits[i]*1000);
            }
        }
    /* Unsupported USB_TYPE must preserve the pre-existing SDP behavior. */
    read_error = -22; dwc.current_limit = 500; writes = 0;
    dwc3_vbus_draw_work(&dwc.vbus_draw_work);
    assert(writes == 1 && written == 500000);
}
'''.replace('CALLBACK', callback)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'test.c').write_text(harness)
            subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', str(path/'test.c'),
                            '-o', str(path/'test')], check=True)
            subprocess.run([str(path/'test')], check=True)


if __name__ == '__main__':
    unittest.main()
