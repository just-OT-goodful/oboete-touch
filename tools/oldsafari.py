"""
Pseudo "old Safari (iOS 12)" test in Chromium.

mode=modern : the built index.html as-is (Chromium supports everything)
mode=broken: same as old but WITHOUT our flex-gap polyfill (shows what old iPads looked like before the fix)
mode=old    : simulate what iOS 12 Safari cannot do, so our fallbacks are what's left:
              - flexbox gap ignored (zeroed at runtime on every flex container) + polyfill forced on
              - clamp() / aspect-ratio / overflow-x:clip declarations dropped,
                @supports not (aspect-ratio) block applied
              - JS APIs newer than Safari 12 deleted
Same seeded Math.random in both modes so the screens are comparable.

usage: python3 tools/oldsafari.py index.html OUTDIR
       VP=ipad_p|ipad_l|phone   only that viewport
       ONLY=cards,bus           only those games
then:  python3 tools/montage.py OUTDIR ipad_p home,shop,cards OUTDIR2   (side-by-side modern | old+fix | old no fix)
Needs: pip install playwright pillow (Chromium).
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

PATH, OUT = sys.argv[1], sys.argv[2]
G = ['shop', 'sushi', 'stars', 'phone', 'bus', 'med', 'cards', 'train', 'cook', 'locker', 'wallet', 'plan']
WAIT = {'shop': 6000, 'sushi': 3000, 'stars': 5000, 'phone': 6000, 'bus': 12000, 'med': 9000, 'cards': 2500,
        'train': 4000, 'cook': 6000, 'locker': 7500, 'wallet': 12000, 'plan': 9000}
VPS = {'ipad_p': (768, 1024), 'ipad_l': (1024, 768), 'phone': (375, 667)}
only_vp = os.environ.get('VP')
ONLY = os.environ.get('ONLY')
if ONLY: G = [g for g in G if g in ONLY.split(',')]

SEED = "(function(){var s=12345;Math.random=function(){s=(s*1103515245+12345)&0x7fffffff;return s/0x80000000}})();"

OLD = r"""
window.__FORCE_NFG = true;
// JS features newer than Safari 12
[[Array.prototype,'flat'],[Array.prototype,'flatMap'],[Array.prototype,'at'],[String.prototype,'replaceAll'],
 [String.prototype,'at'],[String.prototype,'matchAll'],[Object,'fromEntries'],[Object,'hasOwn'],[Promise,'allSettled'],
 [Promise,'any'],[window,'structuredClone'],[window,'queueMicrotask'],[Element.prototype,'replaceChildren'],
 [Element.prototype,'toggleAttribute'],[window,'ResizeObserver']].forEach(function(p){try{delete p[0][p[1]]}catch(e){}});
try{Object.defineProperty(Navigator.prototype,'clipboard',{get:function(){return undefined}})}catch(e){}
try{Object.defineProperty(Navigator.prototype,'wakeLock',{get:function(){return undefined}})}catch(e){}
try{delete crypto.__proto__.randomUUID}catch(e){}
// CSS that iOS 12 drops
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('style').forEach(function(st){
    var t=st.textContent;
    t=t.replace(/@supports not \(aspect-ratio:\s*1\s*\/\s*1\)\s*\{([\s\S]*?)\n\}/,'$1');
    t=t.replace(/^\s*[a-z-]+\s*:[^;{}]*clamp\([^;{}]*;?\s*$/gm,'');
    t=t.replace(/^\s*aspect-ratio\s*:[^;{}]*;?\s*$/gm,'');
    t=t.replace(/^\s*overflow-x\s*:\s*clip\s*;?\s*$/gm,'');
    t=t.replace(/^\s*inset\s*:[^;{}]*;?\s*$/gm,'');
    st.textContent=t;
  });
  window.__simOK=true;
});
// flexbox gap: zero it on every flex container, like iOS 12 ignores it
(function(){
  function zero(){var a=document.querySelectorAll('*');for(var i=0;i<a.length;i++){var e=a[i],d=getComputedStyle(e).display;
    if(d==='flex'||d==='inline-flex'){e.style.setProperty('row-gap','0','important');e.style.setProperty('column-gap','0','important');e.__z=1}
    else if(e.__z){e.style.removeProperty('row-gap');e.style.removeProperty('column-gap');e.__z=0}}}
  document.addEventListener('DOMContentLoaded',function(){zero();
    new MutationObserver(zero).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','hidden']});
    window.addEventListener('resize',zero)});
})();
"""

METRIC = """()=>{const s=document.querySelector('#scene');const r=s&&!s.closest('[hidden]')?s.getBoundingClientRect():null;
 return {sw:document.documentElement.scrollWidth,bottom:r?Math.round(r.bottom+scrollY):null,
 poly:document.querySelectorAll('[style*="margin"]').length,nfg:document.documentElement.className.indexOf('nfg')>=0,
 banner:!!document.getElementById('errbar')}}"""


async def shot(pg, name, d, full=False):
    await pg.wait_for_timeout(250)
    await pg.screenshot(path=os.path.join(d, name + '.png'), full_page=full, animations='disabled')
    return await pg.evaluate(METRIC)


async def run(mode):
    res = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for vp, (w, h) in VPS.items():
            if only_vp and vp != only_vp:
                continue
            d = os.path.join(OUT, mode, vp); os.makedirs(d, exist_ok=True)
            ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=True, has_touch=True,
                                      device_scale_factor=1)
            await ctx.add_init_script(SEED)
            if mode == 'old':
                await ctx.add_init_script(OLD)
            if mode == 'broken':  # same restrictions, but without our flex-gap polyfill
                await ctx.add_init_script(OLD.replace('window.__FORCE_NFG = true;', ''))

            async def page():
                pg = await ctx.new_page(); errs = []
                pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.goto('file://' + PATH); await pg.wait_for_timeout(300)
                return pg, errs

            pg, errs = await page()
            res[f'{vp}/home'] = (await shot(pg, 'home', d, True), errs)
            await pg.click('[data-solo="shop"]')
            res[f'{vp}/solo'] = (await shot(pg, 'solo', d, True), errs)
            for scr, btn in [('records', '#toRecords'), ('about', '#toAbout'), ('users', '#toUsers')]:
                await pg.goto('file://' + PATH); await pg.wait_for_timeout(300)
                await pg.click(btn)
                res[f'{vp}/{scr}'] = (await shot(pg, scr, d, True), errs)
            await pg.close()

            for g in G:
                pg, errs = await page()
                await pg.click(f'[data-solo="{g}"]'); await pg.click('#soloSeg [data-len="1"]')
                await pg.click('#soloStart'); await pg.wait_for_timeout(400)
                if g == 'shop':
                    res[f'{vp}/inter'] = (await shot(pg, 'inter', d), errs)
                await pg.click('#nx'); await pg.wait_for_timeout(WAIT[g])
                res[f'{vp}/{g}'] = (await shot(pg, g, d), errs)
                if g == 'shop':
                    await pg.click('#pauseBtn')
                    res[f'{vp}/pause'] = (await shot(pg, 'pause', d), errs)
                await pg.close()
            await ctx.close()
        await b.close()
    return res


async def main():
    out = {}
    for mode in ['modern', 'old', 'broken']:
        out[mode] = await run(mode)
    json.dump(out, open(os.path.join(OUT, 'metrics.json'), 'w'), ensure_ascii=False, indent=1)
    for k in out['modern']:
        m, o = out['modern'][k], out['old'].get(k)
        print(f'{k:16s} modern sw={m[0]["sw"]} bot={m[0]["bottom"]} err={len(m[1])} | '
              f'old sw={o[0]["sw"]} bot={o[0]["bottom"]} poly={o[0]["poly"]} nfg={o[0]["nfg"]} banner={o[0]["banner"]} err={o[1]}')

asyncio.run(main())
