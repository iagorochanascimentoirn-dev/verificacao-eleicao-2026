# Conta tipos de mensagem (normalizados) em todos os logs de urna de um zip do TSE
import zipfile, subprocess, sys, re, collections, tempfile, os
zp=sys.argv[1]; pat=re.compile(sys.argv[2] if len(sys.argv)>2 else '.', re.I)
z=zipfile.ZipFile(zp); c=collections.Counter(); secs=collections.Counter()
tmp=tempfile.mkdtemp()
for n in [n for n in z.namelist() if n.endswith('-log.jez')]:
    p=os.path.join(tmp,'a.jez'); open(p,'wb').write(z.read(n))
    out=subprocess.run(['7z','x','-so',p],capture_output=True).stdout.decode('latin1')
    seen=set()
    for l in out.splitlines():
        f=l.split('\t')
        if len(f)<5: continue
        m=re.sub(r'\d+','N',f[4])
        if pat.search(m): c[m]+=1; seen.add(m)
    for m in seen: secs[m]+=1
for m,k in c.most_common(): print(k, secs[m], m)
