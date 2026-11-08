__file__='/tmp/xkcd-channel-scratchpad/repair_inner.py'
exec(open(__file__).read().split('ok = dfs(0)')[0])
for k in range(1,60):
    pos,out,done=decode(bytes(data[:k]))
    if done is False: print('fail at prefix',k,'pos',pos,'pix',len(out)); break
for i in range(D0,D0+16): print(i, base[i], [k for _,k,_ in tokens[i]], [f for f,_,_ in tokens[i]])
