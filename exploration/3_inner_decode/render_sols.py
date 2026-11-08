__file__='/tmp/xkcd-channel-scratchpad/repair_inner.py'
exec(open(__file__).read().split('cands = ')[0])
import json, numpy as np
from PIL import Image, ImageDraw
sols=json.load(open(ROOT/'sols.json'))
pick=list(range(0,len(sols),max(1,len(sols)//8)))[:8]
sheet=Image.new('RGB',(4*300,2*230),'white'); dr=ImageDraw.Draw(sheet)
for j,s in enumerate(pick):
    pos,out,done=decode(bytes(sols[s]))
    a=np.array(out+[0]*(NPIX-len(out))).reshape(51,72)
    im=Image.fromarray(((1-a)*255).astype('uint8')).resize((288,204),Image.Resampling.NEAREST)
    x,y=(j%4)*300,(j//4)*230
    sheet.paste(im,(x,y)); dr.text((x,y+208),f'sol {s}',fill='red')
sheet.save(ROOT/'sols.png')
