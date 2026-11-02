#!/bin/sh
# Small HTTP service with durable state for device acceptance tests.
set -eu
umask 022
# Alpine's default BusyBox omits httpd. Bind the validated static Debian
# BusyBox explicitly, and check the applet before starting the workload.
tools=${MI5_TEST_BUSYBOX:-/test-tools/busybox}
"$tools" --list | grep -qx httpd
counter=0
if [ -f /data/counter ]; then
    counter=$(cat /data/counter)
fi
case "$counter" in ''|*[!0-9]*) echo 'Invalid persisted counter' >&2; exit 1;; esac
publish() {
    printf '%s\n' "$counter" > /data/counter.new
    mv /data/counter.new /data/counter
    printf '{"workload":"mi5-acceptance","counter":%s}\n' "$counter" > /data/index.html.new
    mv /data/index.html.new /data/index.html
}
publish
"$tools" httpd -f -p 8080 -h /data &
http_pid=$!
trap 'kill "$http_pid"; wait "$http_pid" || true; exit 0' TERM INT
while kill -0 "$http_pid" 2>/dev/null; do
    sleep 10 &
    wait $! || true
    counter=$((counter + 1))
    publish
done
wait "$http_pid"
