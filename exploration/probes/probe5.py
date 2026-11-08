__file__='/tmp/xkcd-channel-scratchpad/repair_inner.py'
exec(open(__file__).read().split('cands = ')[0])
d=[base[i] for i in range(D0,D1)]
for k in range(1,len(d)+1):
    pos,out,done=decode(bytes(d[:k]))
    if done is False:
        print('fail prefix',k,'token',D0+k-1,'pos',pos,'pix',len(out)); break
else: print('end',done,len(out))
for i in range(D0+k-6,D0+k+1): print(i,base[i],[x[1] for x in tokens[i]],[x[0] for x in tokens[i]])
