#!/bin/bash
# usage: otrun.sh tag   -> oboete-touch sweep in bionic+focal, iPad landscape/portrait (Safari toolbars shown)
TAG=$1; G=${G:-shop,sushi,stars,phone,bus,med,cards,train,cook,locker,wallet,plan}
cd /opt/wk/work
for r in bionic focal; do for v in 1024x661 768x917; do W=${v%x*};H=${v#*x}; d=out/${TAG}_${r}_$v; mkdir -p $d
  python3 tools/otsweep.py /work/ot/index.html /work/$d $W $H $G > plan_${TAG}_${r}_$v.json
  (./run.sh $r /work/plan_${TAG}_${r}_$v.json | grep RESULT | grep -v '"ok": 1\|"ok": true' > $d/result.txt) &
done; done; wait
for f in out/${TAG}_*/result.txt; do echo "=== $f"; python3 - "$f" <<'PY'
import json,sys
for l in open(sys.argv[1]):
    d=json.loads(l[7:]);o=d.get('ok')
    if isinstance(o,dict):
        page=d['id'] in ('home','records','about','users')
        bad=(o['needScroll'] and not page) or o['nBelow'] or o['overflow'] or o.get('inner')
        print(('NG ' if bad else 'ok ')+f"{d['id']:8s} scroll={o['needScroll']}({o['scrollH']}/{o['vh']}) below={o['belowFold'][:2]} inner={o.get('inner',[])[:2]} overflow={o['overflow'][:3]}")
    elif d.get('ok')!=[] : print(d)
PY
done
