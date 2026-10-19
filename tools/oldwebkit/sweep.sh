#!/bin/bash
# usage: sweep.sh tag html  -> runs ddsweep in bionic+focal at iPad landscape/portrait (Safari toolbars+tabs shown)
TAG=$1; HTML=$2; G=${G:-tower,script,errand,sched,trail,cshape,gonogo,stroop,maze,shop,numsw,anti}
cd /opt/wk/work
for r in bionic focal; do for v in 1024x661 768x917; do W=${v%x*};H=${v#*x}; d=out/${TAG}_${r}_$v; mkdir -p $d
  python3 tools/ddsweep.py $HTML /work/$d $W $H $G ${LV:-1} > /opt/wk/work/plan_${TAG}_${r}_$v.json
  (./run.sh $r /work/plan_${TAG}_${r}_$v.json | grep RESULT | grep -v '"ok": 1' > $d/result.txt) &
done; done; wait
for f in out/${TAG}_*/result.txt; do echo "=== $f"; python3 - "$f" <<'PY'
import json,sys
for l in open(sys.argv[1]):
    d=json.loads(l[7:]);o=d.get('ok')
    if isinstance(o,dict):
        bad=o['needScroll'] or o['nBelow'] or o['overflow'] or o.get('inner')
        print(('NG ' if bad else 'ok ')+f"{d['id']:8s} scroll={o['needScroll']}({o['scrollH']}/{o['vh']}) below={o['belowFold'][:2]} inner={o.get('inner',[])[:2]} overflow={o['overflow'][:2]}")
    elif d.get('ok')!=[] : print(d)
PY
done
