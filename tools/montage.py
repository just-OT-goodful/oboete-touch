import sys,os
from PIL import Image, ImageChops, ImageDraw
root,vp,names=sys.argv[1],sys.argv[2],sys.argv[3].split(',')
out=sys.argv[4]; maxh=int(sys.argv[5]) if len(sys.argv)>5 else 1400
for n in names:
    ims=[Image.open(os.path.join(root,m,vp,n+'.png')).convert('RGB') for m in ['modern','old','broken']]
    a,b=ims[0],ims[1]
    h=max(i.height for i in ims); 
    if a.size==b.size:
        d=ImageChops.difference(a,b).convert('L').point(lambda x:255 if x>40 else 0); pct=sum(d.histogram()[255:])/(a.width*a.height)*100
    else: pct=-1
    W=sum(i.width for i in ims)+20
    m=Image.new('RGB',(W,min(h,maxh)+24),'white'); x=0
    dr=ImageDraw.Draw(m)
    for lab,i in zip(['modern','old+fix','old NO fix'],ims):
        m.paste(i.crop((0,0,i.width,min(i.height,maxh))),(x,24)); dr.text((x+4,4),lab,fill='red'); x+=i.width+10
    m.save(os.path.join(out,f'{vp}_{n}.png')); print(n,'diff%',round(pct,2),a.size,b.size)
