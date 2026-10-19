#!/usr/bin/env python3
"""
Real old-WebKit test harness (WebKitGTK 2.20 = ~Safari 11.1/iOS 11.3, 2.28 = ~Safari 13.1/iOS 13.4).
Runs inside the Ubuntu 18.04/20.04 chroot under Xvfb.

usage: python3 wk.py plan.json
plan = {"w":768,"h":920,"steps":[ {"load":"file:///work/x/index.html"}, {"wait":500},
         {"js":"return document.title"}, {"shot":"/work/out/a.png","full":false},
         {"tap":[x,y]}, {"drag":[[x1,y1],[x2,y2],...]} ]}
Every "js" result and errors are printed as JSON lines:  RESULT {...}
"""
import json, sys, time, subprocess
import gi
gi.require_version('Gtk', '3.0'); gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, WebKit2, GLib

plan = json.load(open(sys.argv[1]))
W, H = plan.get('w', 768), plan.get('h', 1024)
UA = plan.get('ua', 'Mozilla/5.0 (iPad; CPU OS 12_5_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.2 Mobile/15E148 Safari/604.1')

win = Gtk.Window(); win.set_default_size(W, H); win.move(0, 0); win.set_decorated(False)
ucm = WebKit2.UserContentManager()
ucm.add_script(WebKit2.UserScript.new(
    "window.__errs=[];window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||'?'))});"
    "window.addEventListener('unhandledrejection',function(e){window.__errs.push('rej:'+(e.reason&&e.reason.message||e.reason))});"
    + plan.get('init', ''),
    WebKit2.UserContentInjectedFrames.ALL_FRAMES, WebKit2.UserScriptInjectionTime.START, None, None))
wv = WebKit2.WebView.new_with_user_content_manager(ucm)
st = wv.get_settings()
st.set_user_agent(UA)
st.set_enable_write_console_messages_to_stdout(True)
try: st.set_allow_file_access_from_file_urls(True)
except Exception: pass
win.add(wv); win.show_all()


def pump(ms):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.004)


def run_js(code):
    """Return value via document.title (works on WebKitGTK 2.20 which lacks the JSC GLib API)."""
    tag = 'R%d' % int(time.time() * 1000)
    src = ("(function(){var o;try{o={ok:(function(){%s})()}}catch(e){o={err:String(e)}}"
           "window.__keep=document.title;document.title='%s:'+JSON.stringify(o)})()" % (code, tag))
    wv.run_javascript(src, None, None, None)
    for _ in range(500):
        pump(10)
        t = wv.get_title() or ''
        if t.startswith(tag + ':'):
            wv.run_javascript("document.title=window.__keep", None, None, None); pump(10)
            return json.loads(t[len(tag) + 1:])
    return {'err': 'timeout'}


def shot(path, full):
    done = []
    def cb(v, res, _):
        try:
            s = v.get_snapshot_finish(res); s.write_to_png(path); done.append(1)
        except Exception as e:
            print('SHOTERR', e); done.append(0)
    region = WebKit2.SnapshotRegion.FULL_DOCUMENT if full else WebKit2.SnapshotRegion.VISIBLE
    wv.get_snapshot(region, WebKit2.SnapshotOptions.NONE, None, cb, None)
    for _ in range(1000):
        pump(10)
        if done: break


def xdo(*a):
    subprocess.call(['xdotool'] + [str(x) for x in a])


for s in plan['steps']:
    if 'load' in s:
        wv.load_uri(s['load'])
        for _ in range(1500):
            pump(10)
            if not wv.is_loading(): break
        pump(s.get('settle', 600))
    elif 'wait' in s:
        pump(s['wait'])
    elif 'js' in s:
        r = run_js(s['js']); print('RESULT ' + json.dumps({'id': s.get('id'), **r}, ensure_ascii=False)); sys.stdout.flush()
    elif 'shot' in s:
        shot(s['shot'], s.get('full', False))
    elif 'tap' in s:
        x, y = s['tap']; xdo('mousemove', x, y); pump(40); xdo('click', 1); pump(s.get('after', 300))
    elif 'drag' in s:
        pts = s['drag']; xdo('mousemove', pts[0][0], pts[0][1]); pump(40); xdo('mousedown', 1); pump(60)
        for (x, y) in pts[1:]:
            xdo('mousemove', x, y); pump(s.get('stepms', 50))
        xdo('mouseup', 1); pump(s.get('after', 300))
r = run_js("return window.__errs")
print('RESULT ' + json.dumps({'id': '__errs', **r}, ensure_ascii=False))
