# generate a WebKit plan that opens every dandori-dojo game and measures overflow
import json,sys
html,out,w,h=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
games=sys.argv[5].split(',')
levels=[int(x) for x in (sys.argv[6] if len(sys.argv)>6 else '1').split(',')]
seed="Math.random=(function(){var s=7;return function(){s=(s*1103515245+12345)&0x7fffffff;return s/0x80000000}})();"
MEASURE=r"""
function vis(e){var s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&e.getClientRects().length}
var vw=innerWidth,vh=innerHeight,out=[],scr=document.querySelector('.screen:not([hidden])'),A=document.getElementById('area');
var root=scr||document.body,els=root.querySelectorAll('*');
for(var i=0;i<els.length&&out.length<25;i++){var e=els[i];if(!vis(e))continue;var r=e.getBoundingClientRect();if(r.width<2||r.height<2)continue;
  var p=e.parentElement;while(p&&p!==root){var ps=getComputedStyle(p);if(ps.overflow!=='visible'||ps.backgroundColor!=='rgba(0, 0, 0, 0)'||ps.borderTopWidth!=='0px'||ps.boxShadow!=='none')break;p=p.parentElement}
  var reason='';
  if(r.right>vw+1||r.left<-1)reason='outside-viewport-x';
  else if(p&&p!==root){var q=p.getBoundingClientRect();if(r.left<q.left-2||r.right>q.right+2||r.top<q.top-2||r.bottom>q.bottom+2)reason='outside-frame '+(p.id||p.className).toString().slice(0,30)+' by '+Math.round(Math.max(q.left-r.left,r.right-q.right,q.top-r.top,r.bottom-q.bottom))+'px'}
  if(reason){var tag=e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+(typeof e.className==='string'&&e.className?'.'+e.className.split(' ')[0]:'');out.push(tag+' : '+reason)}}
var sh=document.documentElement.scrollHeight,bh=document.body.scrollHeight;
var below=[];if(A){var bs=A.querySelectorAll('button,[data-c],.item,.opt');for(var j=0;j<bs.length;j++){var rr=bs[j].getBoundingClientRect();if(vis(bs[j])&&rr.bottom>vh+1)below.push((bs[j].textContent||bs[j].className||'').toString().trim().slice(0,12)+'@'+Math.round(rr.bottom))}}
var inner=[];var al=root.querySelectorAll('*');for(var k=0;k<al.length;k++){var q=al[k],cs=getComputedStyle(q);if(!vis(q))continue;if((cs.overflowY==='auto'||cs.overflowY==='scroll'||cs.overflow==='auto')&&q.scrollHeight>q.clientHeight+4)inner.push((q.id||q.className).toString().slice(0,20)+' '+q.scrollHeight+'/'+q.clientHeight)}
return {inner:inner,scrollH:Math.max(sh,bh),vh:vh,needScroll:Math.max(sh,bh)>vh+2,belowFold:below.slice(0,8),nBelow:below.length,overflow:out}
"""
st=[]
for g in games:
  for L in levels:
    st+=[{"load":"file://"+html},
         {"js":"try{setLv('%s',%d)}catch(e){};var b=document.querySelector('[data-open=\"%s\"]');if(!b)return 'nobtn';b.click();return 1"%(g,L,g)},{"wait":500},
         {"js":"var b=document.querySelector('[data-pred]');b&&b.click();var s=document.getElementById('startBtn');s&&s.click();return 1"},{"wait":2500},
         {"shot":"%s/%s_L%d.png"%(out,g,L)},
         {"id":"%s@L%d"%(g,L),"js":MEASURE}]
json.dump({"w":w,"h":h,"init":seed,"steps":st},sys.stdout)
