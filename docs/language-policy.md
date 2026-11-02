# English language policy

English is the single language for project documentation, installer messages,
configuration menus, diagnostics and the legacy HUD. Canonical pages live in
`docs/`; localized duplicate trees have been consolidated into English pages.
Historical notes remain historical and do not certify current hardware support.

## Installed system

The generic image generates `en_US.UTF-8` and sets:

```text
LANG=en_US.UTF-8
LANGUAGE=en_US:en
LC_MESSAGES=en_US.UTF-8
```

Login shells also export `LC_ALL=en_US.UTF-8`. SSH's
`00-mi5-language.conf` sets the same English environment on the server, taking
precedence over locale variables forwarded by clients. The phone's Indonesian
user-shell overrides were backed up and removed during deployment. Existing SSH
sessions keep their old environment until they reconnect.

This changes message language and locale formatting. It does not change the
configured time zone, account credentials, Wi-Fi profile, host keys or network
addresses. International SSIDs and filenames remain valid UTF-8 data; their
names are not translated.

Verify from a fresh SSH connection:

```bash
locale
nmcli -f GENERAL.STATE device show wlan0
mi5-config status
```

Expected values include `LANG=en_US.UTF-8`, `LC_ALL=en_US.UTF-8` and English
NetworkManager state descriptions. Installer/helper protocols use stable
English tokens such as `CONNECTED`, `NEED_PASSWORD` and `WRONG_PASSWORD`.

## Validation scope

Language changes do not resolve outstanding charger, input or long-duration
network tests. The [stability gate](stability-plan.md) remains in force.
