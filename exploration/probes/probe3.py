__file__='/tmp/xkcd-channel-scratchpad/repair_inner.py'
exec(open(__file__).read().split('cands = ')[0])
import numpy as np
from PIL import Image
b=open(ROOT/'inner_fixed.gif','rb').read()
pos,out,done=decode(b[D0:D1])
a=np.array(out).reshape(51,72)
pal=np.array([[255,255,255],[0,0,0],[255,0,0],[0,0,255]],dtype='uint8')
Image.fromarray(pal[a]).resize((720,510),Image.Resampling.NEAREST).save(ROOT/'inner_idx.png')
# LZW code trace for first codes
