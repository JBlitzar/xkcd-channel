__file__='/tmp/xkcd-channel-scratchpad/repair_inner.py'
exec(open(__file__).read().split('cands = ')[0])
from collections import Counter
b=open(ROOT/'inner_fixed.gif','rb').read()
pos,out,done=decode(b[D0:D1])
print(done, Counter(out))
import numpy as np
a=np.array(out).reshape(51,72)
for r in a: print(''.join('.#23'[v] for v in r))
