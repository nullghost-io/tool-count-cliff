# The Tool Count Cliff

A field note on why testing a model's tool-calling with one tool in the
payload tells you almost nothing about whether it will call tools at all
once it is wired into a real agent with its real toolset.

This is not a product release and not a tool. It's a field observation:
what actually happened measuring the same model, same backend, same
settings, at two different tool counts, plus a reading of what the public
benchmarks on this already show (and the gap in them). No product or
platform name from the original system is included anywhere in this repo —
the value here is the measurement and the principle, not the implementation
it came from.

## The paper

- 📄 [English (PDF)](paper/en/Tool_Count_Cliff.pdf) · [LaTeX source](paper/en/paper_en.tex)
- 📄 [Español (PDF)](paper/es/El_Precipicio_De_Herramientas.pdf) · [fuente LaTeX](paper/es/paper_es.tex)

**Abstract.** A 9.7B open-weight model, given a single synthetic tool and a
direct instruction to use it, called it correctly and completed a full
tool-result round trip without exception. The same model, same backend,
same sampling settings, wired into a real personal-agent platform's
production toolset (over twenty tools across terminal, file, web, and
messaging capabilities), never attempted a real tool call again across
repeated turns, in two independent surfaces — it wrote the shell command as
prose instead of invoking it. Lowering sampling temperature, the first and
most obvious hypothesis, fixed the isolated case and left the production
case unchanged: the first diagnosis was real but incomplete. Public
benchmarks already document tool-count degradation in mid-size and frontier
models as a gradual accuracy decline; what this field case adds is a small
model's version of the same axis, which looks less like a decline and more
like a cliff — a categorical stop, not a lower score.

## What was measured

1. **Isolated test.** One model, one synthetic tool (`get_weather`), one
   direct system instruction to use it. Called correctly, every time, and
   completed a reinjected tool-result round trip cleanly — the model is not
   incapable of tool-calling in the abstract.
2. **Production test.** The identical model and backend, same sampling
   settings, wired into a real agent's actual deployed toolset (terminal,
   file, web, vision, image generation, speech, browser automation, skill
   loading, scheduled jobs, messaging — composited toolsets exceeding
   twenty individual tools). Across two independent entry surfaces (a chat
   gateway and a direct CLI invocation), the model answered in plain text
   every time: `api_calls=1` in both surfaces' own request logs, meaning it
   never even attempted the tool-call turn a real invocation requires.
3. **The temperature hypothesis, tested and only half right.** The
   deployment's default sampling parameters (temperature 1.0, presence
   penalty 1.5) looked like the obvious culprit — those values favor novel,
   "creative" continuations over literal instruction-following, which is
   exactly backwards for deterministic tool-calling. A low-temperature
   (0.1), zero-presence-penalty variant of the same model fixed the
   isolated case outright and was verified end to end: a real tool call,
   with correctly typed arguments, followed by a clean reinjected-result
   round trip. Wired into the same production toolset, under the identical
   low-temperature variant, the model still never attempted a tool call —
   reproduced on both of the same two independent surfaces. Sampling
   mattered for the single-tool case and did not explain the production
   case at all.

## What the public literature already shows

Tool-count degradation in LLM agents is a documented, if unevenly measured,
phenomenon:

- LangChain's ReAct benchmark found accuracy held for `o1` but fell sharply
  for `o3-mini` and to near zero for `GPT-4o` once domain count passed
  roughly seven (reported via StackOne's tool-count-ceiling analysis).
- Maxim's evaluation of five models across GitHub and Notion tool sets
  found that cutting the available tool count from 48 to 25 improved
  accuracy for every model tested, including Claude Sonnet 4 (66.67% to
  73.33%).
- Anthropic's own reporting on its Tool Search Tool shows Claude Opus 4.5
  moving from 79.5% to 88.1% on an internal benchmark once tools are
  discovered on demand instead of all declared up front (vendor-reported,
  on the vendor's own benchmark).
- TSCG (May 2026) reports restoring Phi-4 14B from 0% to 84.4% accuracy at
  20 tools through schema compilation — a mid-size model hitting the same
  kind of wall a 9.7B model hit here, at a comparable tool count.
- A practitioner analysis of this literature states the gap plainly: no
  public benchmark cleanly publishes the size-decay axis — hold the model
  fixed, vary tool count, plot accuracy. Most published numbers compare
  different models at one tool count, or one model at two tool counts
  chosen for a specific product claim, not a curve.

## What this field case adds

The benchmarks above describe *decay* — accuracy drops as tool count rises,
but it rarely reaches zero for a model that could use tools at all. The
9.7B model measured here did not decay. At the isolated tool count it was
reliable; at the production tool count it made zero real tool calls across
every turn observed, on two independent surfaces, under two different
sampling regimes. That is closer to a step function than a slope, and it
is a data point the practitioner-identified gap above does not yet have:
what the same-model, fixed-settings, varied-tool-count curve looks like for
a small open-weight model rather than a frontier or mid-size one.

## The pattern

[`patterns/01_isolated_vs_production_toolset.py`](patterns/01_isolated_vs_production_toolset.py)
is a minimal, runnable illustration of the engineering fix: certify a
model's tool-calling against the actual tool count it will run with in
production, not against whatever count was cheapest to write a smoke test
for. Written from scratch for this repo, no dependencies beyond the
standard library.

```bash
python3 patterns/01_isolated_vs_production_toolset.py
```

## Methodological note

This is a single field case, not a controlled study across multiple models
or tool sets. The two tool counts, the sampling settings, and the
`api_calls` figures cited are real measurements from the same system across
two independent entry surfaces, not simulated. No causal claim is made
about mechanism (attention dilution, instruction dilution from a longer
system prompt, or something else) — only that the isolated-tool-count test
and the production-tool-count test produced categorically different
results for the same model under the same settings, and that this should
make anyone certifying a small model's tool-calling capability test it at
the tool count it will actually run with.

## References

- StackOne. [The Agent Tool Count Ceiling](https://www.stackone.com/blog/agent-tool-count-ceiling/).
- Maxim AI. [Tool Chaos No More: How We're Measuring Model-Tool Accuracy in the Age of MCP](https://www.getmaxim.ai/blog/tool-chaos-no-more-how-were-measuring-model-tool-accuracy-in-the-age-of-mcp/).
- BenchmarkList. [TSCG: Deterministic Tool-Schema Compilation for Agentic LLM Deployments](https://benchmarklist.com/benchmarks/tscg_deterministic_tool_schema_compilation_for_agentic_llm_deployments/).
- HackerNoon. [AI Agents Pick the Wrong Tool More Often as You Add Tools, and Research Shows Why](https://hackernoon.com/ai-agents-pick-the-wrong-tool-more-often-as-you-add-tools-and-research-shows-why).

---

# El precipicio de herramientas *(ES)*

Una nota de campo sobre por qué probar el tool-calling de un modelo con una
sola herramienta en el payload casi no dice nada sobre si ese modelo va a
llamar herramientas cuando se conecte a un agente real con su catálogo
completo de herramientas.

Esto no es el lanzamiento de un producto ni una herramienta. Es una
observación de campo: lo que realmente pasó al medir el mismo modelo, el
mismo backend, los mismos parámetros, en dos conteos de herramientas
distintos, más una lectura de lo que ya muestran los benchmarks públicos
sobre esto (y el hueco que dejan). Ningún nombre de producto o plataforma
del sistema original aparece en este repo — lo que vale aquí es la medición
y el principio, no la implementación de la que salió.

El paper completo está en `paper/es/` (PDF + fuente LaTeX). El patrón de
código en `patterns/` es el mismo de arriba, aplicable sin importar el
idioma.

## Licencia

MIT — ver [LICENSE](LICENSE).
