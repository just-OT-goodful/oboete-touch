#!/bin/bash
# 本物の古いWebKitで画面を確認するための環境を作る（root権限・Ubuntuのパッケージサーバーへの接続が必要）
#   bionic = Ubuntu 18.04 の WebKitGTK 2.20（≒ Safari 11.1 / iOS 11.3〜12）
#   focal  = Ubuntu 20.04 の WebKitGTK 2.28（≒ Safari 13.1 / iOS 13.4〜14）
# 注意：-updates を入れると WebKit が新しくなってしまうので、リリース時点の版だけを使う
set -e
apt-get install -y debootstrap
INC=libwebkit2gtk-4.0-37,gir1.2-webkit2-4.0,python3-gi,python3-gi-cairo,xvfb,xdotool,fonts-noto-cjk,fonts-noto-color-emoji,dbus,dbus-x11,xauth,ca-certificates
mkdir -p /opt/wk/work
for r in bionic focal; do
  [ -d /opt/wk/$r/usr ] || debootstrap --variant=minbase --components=main,universe --include=$INC $r /opt/wk/$r http://archive.ubuntu.com/ubuntu
  R=/opt/wk/$r
  mountpoint -q $R/proc || mount -t proc proc $R/proc
  mountpoint -q $R/dev  || mount --rbind /dev $R/dev
  mountpoint -q $R/sys  || mount --rbind /sys $R/sys
  mkdir -p $R/work; mountpoint -q $R/work || mount --bind /opt/wk/work $R/work
done
cp "$(dirname "$0")"/{wk.py,run.sh} /opt/wk/work/; mkdir -p /opt/wk/work/tools /opt/wk/work/out
cp "$(dirname "$0")"/{ddsweep.py,otsweep.py,sweep.sh,otrun.sh} /opt/wk/work/tools/; chmod +x /opt/wk/work/run.sh /opt/wk/work/tools/*.sh
echo "ready: /opt/wk/work/run.sh bionic /work/plan.json"
