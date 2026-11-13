# The Cliff Was the Context Window

A 9.7B open-weight model behind a local inference server passed a one-tool smoke test and then never called a tool once it was connected to an agent with 24 tool schemas. Sweeping the number of tools made it look like a cliff between 8 and 16 tools. It was a silent prompt truncation: the request weighed 14,095 tokens, the server's default window was 4,096, and the server cut the prompt to about 2,050 tokens without telling the client, dropping the front of the prompt, where the tool schemas sit.

- Paper (EN): [paper/en/The_Cliff_Was_the_Context_Window.pdf](paper/en/The_Cliff_Was_the_Context_Window.pdf) · [LaTeX](paper/en/paper_en.tex)
- Paper (ES): [paper/es/El_Precipicio_Era_La_Ventana.pdf](paper/es/El_Precipicio_Era_La_Ventana.pdf) · [fuente LaTeX](paper/es/paper_es.tex)

## Results

Qwen3.5 9B (Q4_K_M), Ollama 0.33.2, ten trials per cell. "Correct" means a call to the right tool with the right command. Exact 95% intervals: 0 of 10 is 0 to 31%, 10 of 10 is 69 to 100%.

| Experiment | Window 4,096 | Window 32,768 |
|---|---|---|
| Real agent request (24 tools, 14,095 tokens), default sampling | 0/10 | 10/10 |
| Same request, temperature 0.1, presence penalty 0 | 0/10 | 9/10 |
| One tool, short prompt (1,317 tokens) | 10/10 | 10/10 |
| Sweep, 1 to 24 real tool schemas, short prompt | 10, 9, 10, 9, 2, 2 of 10 | 10 of 10 at every point |
| Synthetic control, 1 tool padded to 6,594 and 9,943 tokens | 0/10, 0/10 | 10/10, 10/10 |
| Synthetic control, 16 and 24 tools at the same sizes | 0/10, 0/10 | 10/10, 10/10 |

What the data say:

- The server logged `truncating input prompt` (limit 2,050, prompt 14,095) 50 times at 4,096 and never at 32,768. The response carried no error, and `usage.prompt_tokens` reported 2,050.
- A probe at 4,096 showed the model could not see a marker placed at the start of the system message and listed skill names instead of its tool functions. At 32,768 it saw both markers and all 24 function names.
- The failure follows prompt size against the window, not tool count: one tool padded to the size of 24 fails and succeeds exactly where the 24-tool request does.
- Lowering the sampling temperature changed nothing in either window.
- A Modelfile variant with `PARAMETER num_ctx 32768` on an otherwise default server gave a correct call in 5 of 5 trials with no truncation warnings.

Full tables: [results/field_replay_summary.md](results/field_replay_summary.md), [results/control_summary.md](results/control_summary.md). Raw data: [results/field_replay_raw.csv](results/field_replay_raw.csv), [results/control_raw.jsonl](results/control_raw.jsonl). Token breakdown of the real request: [results/tokens_breakdown.json](results/tokens_breakdown.json) (tools 9,686, agent instructions 4,372, user message 20, chat template 17).

## What to check first

1. Compare `usage.prompt_tokens` in the response with what you sent.
2. Search the server log for `truncating input prompt`, and read the `CONTEXT` column of `ollama ps`.
3. When going through the OpenAI-compatible `/v1` endpoint, set the window in the model (Modelfile), not in request options. Ollama's docs say that API has no way to set the context size.
4. Certify tool use with the production payload, not with the smoke test.

## Reproduce

The harness uses only the Python standard library and a synthetic toolset, so it needs no private data.

```bash
printf 'FROM qwen3.5:9b\nPARAMETER num_ctx 32768\n' > Modelfile
ollama create ctx32k -f Modelfile
python3 harness/ctx_cliff.py --model qwen3.5:9b --calib-model ctx32k --label ctx4096
python3 harness/ctx_cliff.py --model ctx32k --calib-model ctx32k --label ctx32768
```

The first run uses whatever window your server defaults to (it depends on VRAM; 4,096 on the machine used here), so check `ollama ps`. To capture a request from your own agent, run `python3 harness/capture_proxy.py 18434` and point the agent's base URL to `http://127.0.0.1:18434/v1`. The captures contain the agent's full prompt, so do not publish them. Tables for the paper are generated with `python3 results/build_tables.py`.

## What is not here

The captured request itself, the agent's instructions and the model's response texts are not published: they contain private configuration. The tables and token counts come from them. The agent framework is not named; the measurement does not depend on it.

## Limits

One model, one server version, one machine (17.8 GiB of VRAM), one task (run one shell command), ten trials per cell, reasoning effort medium. The original server configuration on the day of the failure was not recorded: the replay reproduces the same prose answers at the default window, which is consistent with the original runs being truncated the same way but does not prove it.

## Correction

An earlier version of this repository, titled "The Tool Count Cliff", claimed a categorical collapse of small models past some number of tools and cited a gap in the public literature. Those claims were wrong. Tool count did not matter once the prompt fit the window, and the cited literature gap was not supported by the source it was attributed to. The measurements here replace that version.

## References

- LangChain. [Benchmarking Single Agent Performance](https://blog.langchain.com/react-agent-benchmarking). February 10, 2025.
- Maxim AI. [How We're Measuring Model-Tool Accuracy in the Age of MCP](https://www.getmaxim.ai/blog/tool-chaos-no-more-how-were-measuring-model-tool-accuracy-in-the-age-of-mcp/). July 2025.
- Anthropic. [Introducing advanced tool use on the Claude Developer Platform](https://www.anthropic.com/engineering/advanced-tool-use). November 24, 2025.
- F. Sakizli. [TSCG: Deterministic Tool-Schema Compilation for Agentic LLM Deployments](https://arxiv.org/abs/2605.04107). arXiv:2605.04107, May 2026.
- Ollama. [Context length](https://docs.ollama.com/context-length) and [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).

---

# El precipicio era la ventana de contexto *(ES)*

Un modelo de pesos abiertos de 9.7B, detrás de un servidor de inferencia local, pasó una prueba de humo con una herramienta y después no llamó ninguna al conectarlo a un agente con 24 esquemas. Al barrer el número de herramientas pareció haber un precipicio entre 8 y 16. Era un recorte silencioso del prompt: la petición pesaba 14,095 tokens, la ventana por defecto del servidor era de 4,096, y el servidor recortó el prompt a unos 2,050 tokens sin avisarle al cliente, descartando el inicio, que es donde van los esquemas de las herramientas.

El paper completo está en `paper/es/` (PDF y fuente LaTeX). Resultados:

| Experimento | Ventana 4,096 | Ventana 32,768 |
|---|---|---|
| Petición real del agente (24 herramientas, 14,095 tokens), muestreo por defecto | 0/10 | 10/10 |
| Misma petición, temperatura 0.1, sin penalización de presencia | 0/10 | 9/10 |
| Una herramienta, prompt corto (1,317 tokens) | 10/10 | 10/10 |
| Barrido de 1 a 24 esquemas reales, prompt corto | 10, 9, 10, 9, 2, 2 de 10 | 10 de 10 en todos |
| Control sintético, 1 herramienta con relleno a 6,594 y 9,943 tokens | 0/10, 0/10 | 10/10, 10/10 |
| Control sintético, 16 y 24 herramientas con esos tamaños | 0/10, 0/10 | 10/10, 10/10 |

Qué revisar primero: compara `usage.prompt_tokens` con lo que enviaste, busca `truncating input prompt` en el log del servidor, lee la columna `CONTEXT` de `ollama ps`, y si pasas por `/v1` fija la ventana en el Modelfile (`PARAMETER num_ctx`), no en las opciones de la petición. Certifica el uso de herramientas con la carga de producción, no con la prueba de humo.

Cómo reproducirlo, qué no se publica (la petición capturada y los textos de respuesta, por contener configuración privada), los límites y la corrección de la versión anterior están en la sección en inglés de arriba.

## Licencia

MIT, ver [LICENSE](LICENSE).
