# WebKit plan for oboete-touch: every game (solo, 1 round), measure overflow / scroll / inner-scroll + home & other screens
import json,sys
html,out,w,h=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
games=sys.argv[5].split(',')
WAIT={'shop':6000,'sushi':3000,'stars':5000,'phone':6000,'bus':12000,'med':9000,'cards':2500,'train':4000,'cook':6000,'locker':7500,'wallet':12000,'plan':9000}
seed="Math.random=(function(){var s=12345;return function(){s=(s*1103515245+12345)&0x7fffffff;return s/0x80000000}})();"
MEASURE=open('/opt/wk/work/tools/ddsweep.py').read().split('MEASURE=r"""')[1].split('"""')[0]
MEASURE=MEASURE.replace("A=document.getElementById('area')","A=document.getElementById('scene')")
st=[]
for scr,btn in [('home',None),('records','#toRecords'),('about','#toAbout'),('users','#toUsers')]:
    st+=[{"load":"file://"+html}]
    if btn: st+=[{"js":"document.querySelector('%s').click();return 1"%btn},{"wait":400}]
    st+=[{"shot":"%s/%s.png"%(out,scr),"full":True},{"id":scr,"js":MEASURE}]
for g in games:
    st+=[{"load":"file://"+html},
         {"js":"document.querySelector('[data-solo=\"%s\"]').click();document.querySelector('#soloSeg [data-len=\"1\"]').click();document.getElementById('soloStart').click();return 1"%g},{"wait":500},
         {"js":"var b=document.getElementById('nx');b&&b.click();return !!b"},{"wait":WAIT[g]},
         {"shot":"%s/%s.png"%(out,g)},{"id":g,"js":MEASURE}]
json.dump({"w":w,"h":h,"init":seed,"steps":st},sys.stdout)
