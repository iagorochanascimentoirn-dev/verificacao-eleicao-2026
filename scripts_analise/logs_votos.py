# Extrai, voto a voto, horario e tipo de habilitacao dos logs de urna (zip do TSE por UF/turno)
# uso: python3 -I logs_votos.py <zip> <saida.csv> <saida_secoes.csv>
import zipfile, subprocess, sys, re, csv, tempfile, os, collections
zp, outv, outs = sys.argv[1:4]
z=zipfile.ZipFile(zp); tmp=tempfile.mkdtemp(); p=os.path.join(tmp,'a.jez')
rx=re.compile(r'o\d{5}([a-z]{2})(\d{5})(\d{4})(\d{4})-log')
fv=open(outv,'w',newline=''); wv=csv.writer(fv)
wv.writerow(['uf','mun','zona','secao','urna','t_hab','t_voto','tipo','tent_bio','manual_req','suspenso'])
fs=open(outs,'w',newline=''); ws=csv.writer(fs)
ws.writerow(['uf','mun','zona','secao','contingencia','n_urnas','inicio','fim','eventos'])
for n in sorted(x for x in z.namelist() if x.endswith('-log.jez')):
    m=rx.search(n); uf,mun,zona,sec=m.groups()
    open(p,'wb').write(z.read(n))
    # .jez pode conter outro .jez (log da urna original quando houve contingencia): extrai recursivo
    wd=tempfile.mkdtemp(dir=tmp); pend=[p]; txts=[]
    while pend:
        a=pend.pop(); od=tempfile.mkdtemp(dir=wd)
        subprocess.run(['7z','x','-y',a,'-o'+od],capture_output=True)
        for root,_,fs_ in os.walk(od):
            for f in fs_:
                fp=os.path.join(root,f)
                if f.endswith('.jez'): pend.append(fp)
                elif f.startswith('logd'): txts.append(open(fp,'rb').read().decode('latin1'))
    txt='\n'.join(txts)
    subprocess.run(['rm','-rf',wd])
    rows=[l.split('\t') for l in txt.splitlines()]
    rows=[r for r in rows if len(r)>=5]
    dias=collections.Counter(r[0][:10] for r in rows if r[4]=='O voto do eleitor foi computado')
    if not dias: continue
    # log e cumulativo (urna do 2o turno traz o 1o): usa o ULTIMO dia com votos
    dia=max(dias,key=lambda d:(d[6:10],d[3:5],d[0:2]))
    cyc=dict(bio=False,tent=0,man=False,susp=False,hab=None)
    urnas=set(); cont=False; ini=fim=None; nev=0
    for r in rows:
        if not r[0].startswith(dia): continue
        nev+=1; msg=r[4]; t=r[0][11:19]; urnas.add(r[2])
        if 'Urna de contingência' in msg: cont=True
        if msg.startswith('Solicita digital. Tentativa'): cyc['tent']+=1
        elif msg=='Tipo de habilitação do eleitor [biométrica]': cyc['bio']=True
        elif msg.startswith('Solicitação de dado pessoal do eleitor para habilitação manual'): cyc['man']=True
        elif msg=='Eleitor foi habilitado': cyc['hab']=t; ini=ini or t
        elif msg.startswith('Eleitor foi suspenso'): cyc['susp']=True
        elif msg.startswith('Habilitação cancelada'):
            cyc=dict(bio=False,tent=0,man=False,susp=False,hab=None)
        elif msg=='O voto do eleitor foi computado':
            tipo='biometrica' if cyc['bio'] else ('manual_apos_falha' if cyc['man'] else ('sem_biometria' if cyc['tent']==0 else 'outro'))
            wv.writerow([uf,mun,zona,sec,r[2],cyc['hab'],t,tipo,cyc['tent'],int(cyc['man']),int(cyc['susp'])])
            fim=t; cyc=dict(bio=False,tent=0,man=False,susp=False,hab=None)
    ws.writerow([uf,mun,zona,sec,int(cont),len(urnas),ini,fim,nev])
fv.close(); fs.close()
