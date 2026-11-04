# Baixa e imprime o log de uma secao (via HTTP Range). uso: log_secao.py <1t|2t> <UF> <mun> <zona> <secao> <saida.txt>
import sys, zipfile, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logs_brasil as L
t, uf, mun, zona, sec, out = sys.argv[1:7]
rf = L.RangeFile(L.URL.format(t=t, uf=uf)); z = zipfile.ZipFile(rf)
tag = f'{uf.lower()}{int(mun):05d}{int(zona):04d}{int(sec):04d}-log.jez'
i = next(i for i in z.infolist() if i.filename.endswith(tag))
txt = L.log_text(L.fetch_member(rf.url, i.header_offset, i.compress_size, i.compress_type), tempfile.mkdtemp())
open(out, 'w').write(txt); print(i.filename, len(txt.splitlines()), 'linhas')
