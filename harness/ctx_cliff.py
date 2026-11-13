"""Control sintético: ¿el modelo deja de llamar herramientas por cuántas son o por cuánto pesa el prompt?

Sin dependencias (solo biblioteca estándar). Contra un servidor compatible con OpenAI, p. ej. Ollama.

Celdas (la herramienta objetivo siempre es `terminal`; el resto son distractores sintéticos):
  A, "N herramientas":  k herramientas con un prompt de sistema corto.
  B, "1 herramienta + relleno": UNA herramienta y el prompt de sistema alargado con texto neutro
     hasta el mismo número de tokens que la celda A correspondiente.
Si A y B fallan al mismo tamaño total, el factor es el tamaño del prompt contra la ventana, no el número de herramientas.

Uso:
  python3 ctx_cliff.py --model qwen3.5:9b --calib-model tcc-ctx-32k --label ctx4096 --trials 10
  --calib-model debe tener una ventana >= 16k: sirve para medir cuánto pesa cada celda sin recorte.
"""
import argparse, json, random, sys, time, urllib.request
from math import comb

WORDS = ('registro cola servicio nodo reporte archivo sesión regla permiso entrega cambio versión mensaje cuenta '
         'tarea proyecto lectura escritura filtro destino origen límite intervalo estado ciclo ruta valor campo '
         'índice lote bloque turno evento alerta perfil módulo canal fuente salida entrada ventana paso criterio').split()


def prose(n, seed):
    r = random.Random(seed)
    return ' '.join(r.choice(WORDS) for _ in range(n)).capitalize() + '.'


def distractor(i, desc_words):
    return {'type': 'function', 'function': {
        'name': f'tool_{i:02d}_{WORDS[i % len(WORDS)]}',
        'description': prose(desc_words, 1000 + i),
        'parameters': {'type': 'object', 'required': ['target'], 'properties': {
            'target': {'type': 'string', 'description': prose(24, 2000 + i)},
            'mode': {'type': 'string', 'enum': ['read', 'write', 'dry_run'], 'description': prose(24, 3000 + i)},
            'limit': {'type': 'integer', 'description': prose(24, 4000 + i)},
            'options': {'type': 'object', 'description': prose(24, 5000 + i)}}}}}


TERMINAL = {'type': 'function', 'function': {
    'name': 'terminal', 'description': 'Run a shell command on this machine and return its output.',
    'parameters': {'type': 'object', 'required': ['command'], 'properties': {
        'command': {'type': 'string', 'description': 'The exact shell command to run.'}}}}}
INSTR = 'When the user asks you to run something, call the matching tool. Never write the command as plain text.'
USER = 'Run: python3 /opt/scripts/status.py'


def toolset(k, desc_words):
    others = [distractor(i, desc_words) for i in range(k - 1)]
    others.insert(round(2 / 3 * (k - 1)), TERMINAL)  # misma posición relativa que en el caso real
    return others


def post(a, model, system, tools, **kw):
    body = {'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': USER}], 'stream': False, **kw}
    if tools: body['tools'] = tools
    req = urllib.request.Request(a.base_url + '/chat/completions', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=600).read())


def size(a, system, tools):
    return post(a, a.calib_model, system, tools, max_tokens=1)['usage']['prompt_tokens']


def pad_to(a, target):
    """Relleno neutro con el mismo total de tokens que la celda A (estimación lineal y dos ajustes)."""
    base = size(a, INSTR, [TERMINAL]); n0 = 1000
    per_word = (size(a, prose(n0, 7) + ' ' + INSTR, [TERMINAL]) - base) / n0
    n = max(0, int((target - base) / per_word))
    for _ in range(2):
        got = size(a, prose(n, 7) + ' ' + INSTR, [TERMINAL])
        n = max(0, n + int((target - got) / per_word))
    return prose(n, 7) + ' ' + INSTR


def clopper_pearson(k, n, a=0.05):
    cdf = lambda p, x: sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(x + 1))
    def bis(f, lo=0.0, hi=1.0):
        for _ in range(60):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if f(m) else (lo, m)
        return (lo + hi) / 2
    lo = 0.0 if k == 0 else bis(lambda m: 1 - cdf(m, k - 1) <= a / 2)
    hi = 1.0 if k == n else bis(lambda m: cdf(m, k) > a / 2)
    return lo, hi


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base-url', default='http://127.0.0.1:11434/v1'); p.add_argument('--model', required=True)
    p.add_argument('--calib-model', required=True); p.add_argument('--label', required=True)
    p.add_argument('--trials', type=int, default=10); p.add_argument('--ks', default='1,4,8,16,24')
    p.add_argument('--desc-words', type=int, default=200, help='palabras por descripción de herramienta distractora')
    p.add_argument('--reasoning', default='medium'); p.add_argument('--out')
    a = p.parse_args()
    out = open(a.out or f'results-{a.label}.jsonl', 'a')
    cells = []
    for k in [int(x) for x in a.ks.split(',')]:
        ts = toolset(k, a.desc_words)
        cells.append(('A', k, INSTR, ts))
        if k > 1:
            cells.append(('B', k, pad_to(a, size(a, INSTR, ts)), [TERMINAL]))
    rows = []
    for cell, k, system, tools in cells:
        sz = size(a, system, tools)
        for t in range(a.trials):
            rec = dict(label=a.label, cell=cell, k=k, n_tools=len(tools), trial=t, model=a.model, tokens_unclipped=sz)
            t0 = time.time()
            try:
                o = post(a, a.model, system, tools, reasoning_effort=a.reasoning)
                m = o['choices'][0]['message']; tc = m.get('tool_calls') or []
                rec.update(prompt_tokens=o['usage']['prompt_tokens'], real_call=bool(tc), calls=[c['function']['name'] for c in tc],
                           terminal_ok=any(c['function']['name'] == 'terminal' and 'status.py' in c['function']['arguments'] for c in tc),
                           prose_cmd=('status.py' in (m.get('content') or '')) and not tc)
            except Exception as e:
                rec['error'] = repr(e)[:160]
            rec['secs'] = round(time.time() - t0, 1); rows.append(rec); out.write(json.dumps(rec) + '\n'); out.flush()
            print(cell, k, t, rec.get('terminal_ok'), rec.get('prompt_tokens'), flush=True)
    print(f'\n| celda | herramientas | tokens sin recorte | tokens recibidos | llamada correcta | IC 95% |\n|---|---|---|---|---|---|')
    for cell, k, system, tools in cells:
        rs = [r for r in rows if r['cell'] == cell and r['k'] == k]; n = len(rs); ok = sum(1 for r in rs if r.get('terminal_ok'))
        lo, hi = clopper_pearson(ok, n); pt = [r['prompt_tokens'] for r in rs if r.get('prompt_tokens')]
        print(f"| {cell} | {len(tools)} | {rs[0]['tokens_unclipped']} | {min(pt)}-{max(pt)} | {ok}/{n} | {lo*100:.0f}-{hi*100:.0f}% |")


if __name__ == '__main__':
    sys.exit(main())
