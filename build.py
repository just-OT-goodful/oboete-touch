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
import json
import os
import re
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
  /* iOS 10以前はこのアプリのプログラムを読めないため、原因不明のエラーではなく分かる言葉で知らせる */
  var iv=/(iPhone|iPad|iPod).* OS (\d+)_/.exec(navigator.userAgent);
  if(iv&&+iv[2]<11){
    window.__OLD_IOS=+iv[2];
    document.addEventListener('DOMContentLoaded',function(){
      var b=document.createElement('div');
      b.setAttribute('style','position:fixed;left:0;right:0;top:0;bottom:0;z-index:100;background:#F4F1EA;color:#1F2A33;font:18px/1.7 sans-serif;padding:40px 28px;text-align:center');
      b.innerHTML='<p style="font-size:22px;font-weight:bold;margin:0 0 12px">この端末ではご利用いただけません</p>'
        +'<p style="margin:0">この端末のiOSはバージョン'+iv[2]+'です。<br>おぼえてタッチは iOS 11 以降で動きます。<br>'
        +'設定 → 一般 → ソフトウェア・アップデート で更新できるかご確認ください。</p>';
      document.body.appendChild(b);
    });
  }
  window.addEventListener('error',function(e){if(window.__OLD_IOS)return;show((e.message||'')+' (行 '+(e.lineno||'?')+')')});
  window.addEventListener('unhandledrejection',function(e){show('Promise: '+(e.reason&&e.reason.message||e.reason))});
  if(!Object.fromEntries){Object.fromEntries=function(a){var o={};for(var i=0;i<a.length;i++){o[a[i][0]]=a[i][1]}return o}}
  /* flexboxのgap（iOS 14.5未満は非対応）が効くか調べ、効かなければ<html class="nfg">にする */
  try{
    var f=document.createElement('div');
    f.style.cssText='display:flex;flex-direction:column;row-gap:1px;position:absolute;visibility:hidden';
    f.appendChild(document.createElement('div'));f.appendChild(document.createElement('div'));
    document.documentElement.appendChild(f);
    var ok=f.scrollHeight===1;f.parentNode.removeChild(f);
    if(!ok||window.__FORCE_NFG)document.documentElement.className+=' nfg';
  }catch(e){}
})();
</script>
'''

# flexboxのgapの代わりに、子要素の余白（margin）で同じ間隔を作る。
# <html class="nfg">（gap非対応のSafari）のときだけ動く。新しいブラウザでは何もしない。
FLEXGAP_POLYFILL = r'''<script>
(function(){
  var D=document.documentElement;if(!/(^|\s)nfg(\s|$)/.test(D.className))return;
  var MAP=__MAP__; /* [メディアクエリ, セレクタ, 行の間隔, 列の間隔] */
  var mqls={},touched=[],pend=false;
  function mm(q){if(!q)return true;if(!window.matchMedia)return false;if(!mqls[q])mqls[q]=window.matchMedia(q);return mqls[q].matches}
  function len(v,el){if(v==null)return 0;var n=parseFloat(v);if(!n)return 0;
    if(/rem$/.test(v))return n*parseFloat(getComputedStyle(D).fontSize);
    if(/em$/.test(v))return n*parseFloat(getComputedStyle(el).fontSize);return n}
  /* 1) 付けた余白を戻す 2) 元の余白を読んで必要な値を足し合わせる 3) まとめて書き込む（読み書きを混ぜない） */
  var accE=[],accV=[];
  function add(c,side,px){if(parseFloat(getComputedStyle(c)['margin'+side])!==0)return; /* 元から余白がある所は触らない */
    var k=accE.indexOf(c);if(k<0){k=accE.length;accE.push(c);accV.push({})}accV[k][side]=(accV[k][side]||0)+px}
  function apply(el,g){
    if(!el.getClientRects().length)return; /* 非表示の画面の中は飛ばす */
    var cs=getComputedStyle(el);if(cs.display.indexOf('flex')<0)return;
    var rg=len(g[0],el),cg=len(g[1],el);if(!rg&&!cg)return;
    var dir=cs.flexDirection||'row',col=dir.indexOf('column')===0,rev=dir.indexOf('reverse')>0,wrap=cs.flexWrap&&cs.flexWrap!=='nowrap';
    var items=[],ns=el.childNodes,i,c,s;
    for(i=0;i<ns.length;i++){c=ns[i];
      if(c.nodeType===3){if(/\S/.test(c.nodeValue))items.push(null)}
      else if(c.nodeType===1){s=getComputedStyle(c);if(s.display==='none'||s.position==='absolute'||s.position==='fixed')continue;items.push(c)}}
    if(items.length<2)return;
    if(wrap){ /* 折り返す行：子に半分ずつ余白を付け、外側の余分は親の負の余白で打ち消す */
      for(i=0;i<items.length;i++){c=items[i];if(!c)continue;
        if(rg){add(c,'Top',rg/2);add(c,'Bottom',rg/2)}if(cg){add(c,'Left',cg/2);add(c,'Right',cg/2)}}
      if(rg){add(el,'Top',-rg/2);add(el,'Bottom',-rg/2)}if(cg){add(el,'Left',-cg/2);add(el,'Right',-cg/2)}
      return}
    var gap=col?rg:cg;if(!gap)return;
    var aft=col?(rev?'Bottom':'Top'):(rev?'Right':'Left'),bef=col?(rev?'Top':'Bottom'):(rev?'Left':'Right');
    for(i=1;i<items.length;i++){if(items[i])add(items[i],aft,gap);else if(items[i-1])add(items[i-1],bef,gap)}
  }
  function run(){
    var i,j,m,els,k,side;
    for(i=0;i<touched.length;i++)touched[i][0].style['margin'+touched[i][1]]='';
    touched=[];accE=[];accV=[];
    var list=[],gaps=[];
    for(i=0;i<MAP.length;i++){m=MAP[i];if(!mm(m[0]))continue;
      try{els=document.querySelectorAll(m[1])}catch(e){continue}
      for(j=0;j<els.length;j++){k=list.indexOf(els[j]);
        if(k<0){list.push(els[j]);gaps.push([m[2],m[3]])}
        else gaps[k]=[m[2]!=null?m[2]:gaps[k][0],m[3]!=null?m[3]:gaps[k][1]]}}
    for(i=0;i<list.length;i++)apply(list[i],gaps[i]);
    for(i=0;i<accE.length;i++)for(side in accV[i]){accE[i].style['margin'+side]=accV[i][side]+'px';touched.push([accE[i],side])}
  }
  function sched(){if(pend)return;pend=true;(window.requestAnimationFrame||setTimeout)(function(){pend=false;try{run()}catch(e){}})}
  function el(nl){for(var j=0;j<nl.length;j++)if(nl[j].nodeType===1)return true;return false}
  try{new MutationObserver(function(ms){for(var i=0;i<ms.length;i++){var x=ms[i];
      if(x.type==='attributes'||el(x.addedNodes)||el(x.removedNodes)){sched();return}}})
    .observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden']})}catch(e){}
  window.addEventListener('resize',sched);window.addEventListener('orientationchange',sched);
  run();
})();
</script>
'''


# ---------- CSS: fallbacks for old Safari ----------

def split_args(s):
    """'a, min(b,c), d' -> ['a', 'min(b,c)', 'd'] (parenthesis-aware)"""
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip()); cur = ''
        else:
            cur += ch
    out.append(cur.strip())
    return out


def replace_fn(value, names, fn):
    """Replace every name(...) call in value (innermost-safe, parenthesis-aware) with fn(name, args)."""
    pat = re.compile(r'(?<![-\w])(' + '|'.join(names) + r')\(')
    while True:
        m = pat.search(value)
        if not m:
            return value
        i, depth = m.end(), 1
        while depth:
            if value[i] == '(':
                depth += 1
            elif value[i] == ')':
                depth -= 1
            i += 1
        args = split_args(value[m.end():i - 1])
        value = value[:m.start()] + fn(m.group(1), args) + value[i:]


def pick(name, args):
    """Plain value for browsers without min()/max()/clamp() (iOS 11.2 and earlier).
    min(): the relative (%/vw) argument, so nothing overflows on a small screen.
    clamp(lo, mid, hi): hi — the app is tablet-first."""
    if name == 'clamp':
        return args[2]
    rel = [a for a in args if re.search(r'%|vw|vh', a)]
    return (rel or args)[0]


def to_minmax(name, args):
    """clamp(a,b,c) -> max(a,min(b,c)) for Safari 11.1–13.0 (iOS 11.3–13.3, e.g. iPad Air 1 on iOS 12)."""
    if name == 'clamp':
        return f'max({args[0]},min({args[1]},{args[2]}))'
    return f'{name}({",".join(args)})'


DECL = re.compile(r'(?<=[{;])(\s*)([a-z-]+)\s*:\s*([^;{}]+?)\s*(?=[;}])')


def css_fallbacks(css):
    def fix(m):
        ws, prop, val = m.group(1), m.group(2), m.group(3)
        out = []
        if re.search(r'(?<![-\w])(clamp|min|max)\(', val):
            plain = replace_fn(val, ['clamp', 'min', 'max'], pick)
            out.append(f'{prop}:{plain}')
            if 'clamp(' in val:
                out.append(f'{prop}:{replace_fn(val, ["clamp"], to_minmax)}')
        if prop in ('gap', 'row-gap', 'column-gap'):  # iOS 11 grid needs the old prefixed name
            out.append(f'grid-{prop}:{val}')
        out.append(f'{prop}:{val}')
        return ws + ';'.join(out)
    return DECL.sub(fix, css)


def css_rules(text, ctx=''):
    """Yield (media_condition, selector, body). Handles @media/@supports blocks (one level)."""
    i = 0
    while i < len(text):
        j = text.find('{', i)
        if j < 0:
            break
        sel = text[i:j].strip()
        if sel.startswith('@'):
            depth, k = 1, j + 1
            while depth:
                depth += {'{': 1, '}': -1}.get(text[k], 0)
                k += 1
            inner = text[j + 1:k - 1]
            if sel.startswith('@media'):
                yield from css_rules(inner, sel[len('@media'):].strip())
            elif sel.startswith('@supports'):
                yield from css_rules(inner, ctx)
            i = k
            continue
        k = text.find('}', j)
        yield ctx, sel, text[j + 1:k]
        i = k + 1


def flexgap_map(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out = []
    for mq, sel, body in css_rules(css):
        if '::' in sel or 'focus-visible' in sel:
            continue
        rg = cg = None
        for prop, val in re.findall(r'(?<![-\w])(gap|row-gap|column-gap)\s*:\s*([^;]+)', body):
            v = val.strip().split()
            if prop == 'gap':
                rg, cg = v[0], (v[1] if len(v) > 1 else v[0])
            elif prop == 'row-gap':
                rg = v[0]
            else:
                cg = v[0]
        if rg is not None or cg is not None:
            out.append([mq, sel.replace('\n', ' '), rg, cg])
    return out

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

    # --- CSS: fallbacks (clamp/min, grid-gap) + esbuild lowering (inset, -webkit- prefixes) ---
    ms = re.search(r'<style>(.*?)</style>', src, re.S)
    css = ms.group(1)
    gap_map = flexgap_map(css)
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, 'app.css'), os.path.join(tmp, 'app11.css')
        open(a, 'w', encoding='utf-8').write(css_fallbacks(css))
        subprocess.run([ESBUILD, a, '--loader:.css=css', '--target=safari11', '--outfile=' + b,
                        '--log-level=warning'], check=True)
        css = open(b, encoding='utf-8').read()
    src = src[:ms.start()] + '<style>\n' + css + '</style>' + src[ms.end():]

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

    polyfill = FLEXGAP_POLYFILL.replace('__MAP__', json.dumps(gap_map, ensure_ascii=False))
    src = src[:m.start()] + '<script>\n' + js + '</script>\n' + polyfill + src[m.end():]

    i = src.index('<div class="wrap">')
    out = HEAD + src[:i] + '</head>\n<body>\n' + src[i:] + '\n</body>\n</html>\n'
    open(OUT, 'w', encoding='utf-8').write(out)
    print('built', OUT, len(out), 'chars')


if __name__ == '__main__':
    main()
