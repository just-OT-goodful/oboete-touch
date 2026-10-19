#!/bin/bash
# usage: run.sh bionic|focal plan.json   (runs wk.py inside the chroot under a private Xvfb)
R=$1; PLAN=$2; D=$((RANDOM%400+100))
chroot /opt/wk/$R /bin/bash -c "
export HOME=/tmp LANG=C.UTF-8 NO_AT_BRIDGE=1
Xvfb :$D -screen 0 1400x1200x24 -nolisten tcp >/dev/null 2>&1 & XP=\$!
sleep 1.2
export DISPLAY=:$D
dbus-run-session -- python3 /work/wk.py $PLAN 2>&1 | grep -v -E 'Gtk-WARNING|dbind-WARNING|libEGL|MESA|^$'
kill \$XP 2>/dev/null
"
