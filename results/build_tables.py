"""Genera los fragmentos TeX del paper desde los datos crudos (ninguna cifra se teclea a mano).

Entradas:  field_replay_raw.csv  (replay de la petición capturada, sin texto de respuestas)
           control_raw.jsonl     (control sintético de harness/ctx_cliff.py, ambas ventanas)
Salida:    ../paper/en/generated.tex y ../paper/es/generated.tex
"""
import csv, json, pathlib
from math import comb

R = pathlib.Path(__file__).resolve().parent
ROOT = R.parent


def cp(k, n, a=0.05):
    cdf = lambda p, x: sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(x + 1))
    def bis(f):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if f(m) else (lo, m)
        return (lo + hi) / 2
    return (0.0 if k == 0 else bis(lambda m: 1 - cdf(m, k - 1) <= a / 2)), (1.0 if k == n else bis(lambda m: cdf(m, k) > a / 2))


def frac(ok, n):
    lo, hi = cp(ok, n)
    return f'{ok}/{n}', f'{lo * 100:.0f}--{hi * 100:.0f}\\%'


field = list(csv.DictReader(open(R / 'field_replay_raw.csv')))
for r in field:
    r['ok'] = r['terminal_ok'] == 'True'; r['call'] = r['real_call'] == 'True'; r['n_tools'] = int(r['n_tools'])
    r['pt'] = int(r['prompt_tokens']) if r['prompt_tokens'] else None


def sel(rows, **kw):
    return [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]


def tok_range(rs):
    p = [r['pt'] for r in rs if r['pt']]
    return f'{min(p):,}' if min(p) == max(p) else f'{min(p):,}--{max(p):,}'


H = {
 'en': dict(w='Window', s='Sampling', t='Tools', tk='Tokens in', ok='Correct', ci='95\\% CI', d='default', l='low temp.', f1='Real request (24 tools, 14,095 tokens)', f2='One tool, short prompt',
            cap='Same model, same request, two server windows. “Correct call” = a call to the right tool with the right command.',
            ctl_cap='Synthetic control at equal total tokens. A: $k$ tools. B: one tool, system prompt padded to the same size as A. Correct calls out of 10.',
            c1='Tools', c2='Tokens', c3='A, 4,096', c4='B, 4,096', c5='A, 32,768', c6='B, 32,768'),
 'es': dict(w='Ventana', s='Muestreo', t='Herramientas', tk='Tokens', ok='Correctas', ci='IC 95\\%', d='por defecto', l='temp. baja', f1='Petición real (24 herramientas, 14,095 tokens)', f2='Una herramienta, prompt corto',
            cap='Mismo modelo, misma petición, dos ventanas del servidor. “Llamada correcta” = llamada a la herramienta correcta con el comando correcto.',
            ctl_cap='Control sintético con el mismo total de tokens. A: $k$ herramientas. B: una herramienta, prompt de sistema alargado al tamaño de A. Llamadas correctas de 10.',
            c1='Herram.', c2='Tokens', c3='A, 4,096', c4='B, 4,096', c5='A, 32,768', c6='B, 32,768'),
}


def field_table(lang):
    h = H[lang]; rows = []
    for win, lab in (('ctx4096', '4,096'), ('ctx32768', '32,768')):
        for cell, name in (('real_payload', h['f1']), ('isolated_1tool_short', h['f2'])):
            for sm, smn in (('default', h['d']), ('low', h['l'])):
                rs = sel(field, window=win, cell=cell, sampling=sm)
                f, ci = frac(sum(r['ok'] for r in rs), len(rs))
                rows.append(f"{lab} & {smn} & {rs[0]['n_tools']} & {tok_range(rs)} & {f} & {ci} \\\\")
        rows.append('\\midrule' if win == 'ctx4096' else '')
    body = '\n'.join(x for x in rows if x)
    return ('\\begin{table}[H]\\centering\\footnotesize\\setlength{\\tabcolsep}{3.5pt}\\begin{tabular}{@{}llrrrr@{}}\\toprule '
            f"{h['w']} & {h['s']} & {h['t']} & {h['tk']} & {h['ok']} & {h['ci']} \\\\\\midrule\n{body}\n\\bottomrule\\end{{tabular}}\\caption{{{h['cap']}}}\\label{{tab:field}}\\end{{table}}")


def sweep_coords():
    out = {}
    for win in ('ctx4096', 'ctx32768'):
        pts = []
        for i, k in enumerate((1, 2, 4, 8, 16, 24)):
            rs = sel(field, window=win, cell='sweep_short', sampling='default', n_tools=k)
            pts.append(f'({i},{sum(r["ok"] for r in rs)})')
        out[win] = pts
    return out


def draw(pts, color):
    return f'\\draw[line width=1.2pt,color={color}] ' + ' -- '.join(pts) + ';' + ''.join(f'\\fill[{color}] {q} circle (2.4pt);' for q in pts)


def control_table(lang):
    h = H[lang]; p = ROOT / 'results' / 'control_raw.jsonl'
    if not p.exists(): return '\\relax'
    rows = [json.loads(l) for l in open(p)]
    lines = []
    for k in (4, 8, 16, 24):
        cells = []
        for lab in ('ctx4096', 'ctx32768'):
            for c in ('A', 'B'):
                rs = [r for r in rows if r['label'] == lab and r['cell'] == c and r['k'] == k]
                cells.append(frac(sum(1 for r in rs if r.get('terminal_ok')), len(rs))[0] if rs else '--')
        tk = [r['tokens_unclipped'] for r in rows if r['cell'] == 'A' and r['k'] == k][0]
        lines.append(f'{k} & {tk:,} & ' + ' & '.join(cells) + ' \\\\')
    return ('\\begin{table}[H]\\centering\\footnotesize\\setlength{\\tabcolsep}{3.5pt}\\begin{tabular}{@{}rrrrrr@{}}\\toprule '
            f"{h['c1']} & {h['c2']} & {h['c3']} & {h['c4']} & {h['c5']} & {h['c6']} \\\\\\midrule\n" + '\n'.join(lines) +
            f"\n\\bottomrule\\end{{tabular}}\\caption{{{h['ctl_cap']}}}\\label{{tab:control}}\\end{{table}}")


sc = sweep_coords()
for lang in ('en', 'es'):
    tex = (f"\\newcommand{{\\sweepSmall}}{{{draw(sc['ctx4096'], 'barsolid')}}}\n\\newcommand{{\\sweepBig}}{{{draw(sc['ctx32768'], 'nbblue')}}}\n"
           f"\\newcommand{{\\fieldtable}}{{{field_table(lang)}}}\n\\newcommand{{\\controltable}}{{{control_table(lang)}}}\n")
    (ROOT / 'paper' / lang / 'generated.tex').write_text(tex)
print('ok', sc)


def control_md():
    p = ROOT / 'results' / 'control_raw.jsonl'
    if not p.exists(): return
    rows = [json.loads(l) for l in open(p)]
    out = ['| tools in A | tokens (unclipped) | A, window 4,096 | B, window 4,096 | A, window 32,768 | B, window 32,768 |', '|---|---|---|---|---|---|']
    for k in (4, 8, 16, 24):
        cells = []
        for lab in ('ctx4096', 'ctx32768'):
            for c in ('A', 'B'):
                rs = [r for r in rows if r['label'] == lab and r['cell'] == c and r['k'] == k]
                ok = sum(1 for r in rs if r.get('terminal_ok')); lo, hi = cp(ok, len(rs))
                cells.append(f'{ok}/{len(rs)} ({lo*100:.0f}-{hi*100:.0f}%)')
        tk = [r['tokens_unclipped'] for r in rows if r['cell'] == 'A' and r['k'] == k][0]
        out.append(f'| {k} | {tk:,} | ' + ' | '.join(cells) + ' |')
    (ROOT / 'results' / 'control_summary.md').write_text('\n'.join(out) + '\n')


control_md()
