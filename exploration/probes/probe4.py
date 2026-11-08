import json, numpy as np
exec(open('/tmp/xkcd-channel-scratchpad/classify2.py').read().split("rows = []")[0].replace('"ט": 790','"ט": 283'))
tok=json.load(open('/tmp/xkcd-channel-scratchpad/tokens.json'))
def fit(i,k):
    best=None
    for dy in range(-3,4):
        for dx in range(-3,4):
            g=np.roll(np.roll(G[k],dy,0),dx,1)
            r=(int((g&~ink[i]).sum()),int((ink[i]&~g).sum()))
            if best is None or sum(r)<sum(best): best=r
    return best
for t in (113,275,280,292,293,300,305,311,328,332):
    for f,k,c in tok[t]:
        if k in 'הח' or k in 'סט':
            print(t,f,k,c,'ה',fit(f,'ה'),'ח',fit(f,'ח'),'ס',fit(f,'ס'),'ט',fit(f,'ט'))
