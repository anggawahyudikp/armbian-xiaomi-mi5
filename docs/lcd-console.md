# LCD Linux console

The default display is a normal Linux virtual terminal (`tty1`): boot output,
login prompt, then a shell after authentication. It is not the former graphical
HUD. Input normally comes from SSH or an attached input device; no touch keyboard
is provided. SSH and LCD are separate terminal sessions.

`mi5-console.service` loads the panel/MSM modules, selects a readable console font,
and starts the LCD idle controller. It leaves the distribution's getty and
Armbian first-login credentials in control. `gemini-server-mode` manages CPU
availability/governors; it no longer controls backlight brightness.

```sh
sudo mi5-config display status
sudo mi5-config display timeout 300
sudo mi5-config display timeout 0     # disable automatic timeout
sudo mi5-config display brightness 20
sudo mi5-config display sleep
sudo mi5-config display wake
```

Settings persist in `/etc/default/mi5-console`. Timeout is local-input idle time;
SSH traffic and background logs do not keep the LCD awake. Keyboard/touch activity
wakes it. A short Power press toggles it; repeat and release events do not toggle
again. Logind ignores Power for shutdown, so the controller can use it for LCD
control. A long hardware reset remains a firmware/PMIC function.

Sleep switches off the backlight. This conservative mode retains the panel/DRM
state because this board has DSI power-transition workarounds. It does not claim
complete display power-gating. It never offlines CPUs, changes their governor,
suspends the OS, or disconnects networking. Docker continues running.

The previous `display-unblank`/`gemini-fb-ui` HUD services remain disabled. Their
old blank handler also changed CPU availability; do not enable them alongside
`mi5-console`. The hardware-test worklog records software and physical LCD
verification separately.
