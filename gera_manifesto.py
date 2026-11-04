"""Manifesto SHA3-512 de scripts, geradores, figuras e resultados (exclui os PDFs e o próprio manifesto)."""
import hashlib, sys
from pathlib import Path
R = Path(__file__).parent
def h(p):
    x = hashlib.sha3_512()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): x.update(b)
    return x.hexdigest()
fs = sorted([*R.glob('scripts_analise/*.py'), *R.glob('*.py'), *R.glob('*.png'), *R.rglob('dados_logs/**/*')])
fs = [f for f in fs if f.is_file() and f.suffix not in ('.pdf',) and 'MANIFESTO' not in f.name]
with open(R / 'MANIFESTO_SHA3-512.txt', 'w') as o:
    o.write('# SHA3-512 (FIPS 202) — gerado em ' + __import__('datetime').datetime.now().isoformat(timespec='seconds') + '\n')
    for f in fs: o.write(f'{h(f)}  {f.relative_to(R)}\n')
print(len(fs), 'arquivos')
