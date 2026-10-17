#!/usr/bin/env python3
"""
Build GitHub Pages' index.html from src/oboete-touch.html.

src/oboete-touch.html is the single source of truth — a Claude-Artifact-style
HTML fragment (starts with <title>, ends with </script>; no <head>/<body>).
It is published AS-IS to the Claude artifact (modern browser, no build step
needed there).

For GitHub Pages we additionally need to support old iPads (iOS 11+ Safari),
so this script:
  1. Wraps the fragment in a full <!doctype html> document with the head
     meta tags (viewport, PWA/home-screen hints, theme color).
  2. Injects a small plain-ES5 "guard" script that shows a visible on-screen
     error banner on any runtime error/unhandled rejection — there is no way
     to see a physical iPad's console remotely, so this is the only way to
     diagnose a device-specific failure a user reports.
  3. Transpiles the app's <script> body with esbuild --target=safari11, since
     one unsupported syntax construct anywhere in the script (e.g. the old
     ?? / Object.fromEntries usage found 2026-10-17) makes the WHOLE script
     fail to parse on old WebKit, leaving the page visible but totally
     unresponsive to touch.

Usage:
    npm install        # first time only, installs esbuild locally
    python3 build.py
"""
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'oboete-touch.html')
OUT = os.path.join(HERE, 'index.html')
ESBUILD = os.path.join(HERE, 'node_modules', '.bin', 'esbuild')

GUARD = r'''<script>
/* 端末でエラーが起きたとき、画面の下に内容を表示する（原因の確認用） */
(function(){
  function show(msg){
    try{
      var b=document.getElementById('errbar');
      if(!b){b=document.createElement('div');b.id='errbar';
        b.setAttribute('style','position:fixed;left:0;right:0;bottom:0;z-index:99;background:#B4643F;color:#fff;font:14px/1.5 sans-serif;padding:10px 14px;white-space:pre-wrap');
        (document.body||document.documentElement).appendChild(b);}
      b.textContent='エラーが起きました。この表示の写真を送ってください。\n'+msg+'\n'+navigator.userAgent;
    }catch(e){}
  }
  window.addEventListener('error',function(e){show((e.message||'')+' (行 '+(e.lineno||'?')+')')});
  window.addEventListener('unhandledrejection',function(e){show('Promise: '+(e.reason&&e.reason.message||e.reason))});
  if(!Object.fromEntries){Object.fromEntries=function(a){var o={};for(var i=0;i<a.length;i++){o[a[i][0]]=a[i][1]}return o}}
})();
</script>
'''

HEAD = '''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="おぼえてタッチ">
<meta name="theme-color" content="#1B7A6D">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
''' + GUARD


def main():
    if not os.path.exists(ESBUILD):
        raise SystemExit(
            f'esbuild not found at {ESBUILD}.\n'
            f'Run `npm install` in {HERE} first (needs package.json, already in the repo).'
        )

    src = open(SRC, encoding='utf-8').read()
    m = re.search(r'<script>(.*)</script>', src, re.S)
    if not m:
        raise SystemExit(f'No <script>...</script> block found in {SRC}')

    with tempfile.TemporaryDirectory() as tmp:
        app_js = os.path.join(tmp, 'app.js')
        app11_js = os.path.join(tmp, 'app11.js')
        open(app_js, 'w', encoding='utf-8').write(m.group(1))
        subprocess.run(
            [ESBUILD, app_js, '--target=safari11', '--outfile=' + app11_js, '--log-level=warning'],
            check=True,
        )
        js = open(app11_js, encoding='utf-8').read()

    src = src[:m.start()] + '<script>\n' + js + '</script>' + src[m.end():]

    i = src.index('<div class="wrap">')
    out = HEAD + src[:i] + '</head>\n<body>\n' + src[i:] + '\n</body>\n</html>\n'
    open(OUT, 'w', encoding='utf-8').write(out)
    print('built', OUT, len(out), 'chars')


if __name__ == '__main__':
    main()
