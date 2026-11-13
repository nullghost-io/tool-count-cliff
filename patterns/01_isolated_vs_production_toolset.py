"""Pattern 1 — Certify tool-calling against the real toolset, not a smoke test.

A model was smoke-tested with a single tool in its payload: it called it
correctly, every time. The same model, wired into the real agent with its
full production toolset (terminal, file, web, vision, skills, cronjob,
messaging — over twenty entries), never attempted a tool call again. It
wrote the shell command as prose instead of invoking it. Nothing about the
model changed between the two tests. The payload did.

The bug: treating a pass at N=1 as evidence the model is capable at the
production N. The fix: certify at the real deployment's tool count, not at
whatever count made the test convenient to write.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ToolCallResult:
    tool_count: int
    made_a_real_call: bool


# --- The bug, preserved for contrast -------------------------------------

def buggy_certification(run_single_tool_smoke_test) -> bool:
    """Certifies the model as 'can use tools' from a single, convenient
    trial — the trial that happens to be cheapest to write, not the one
    that matches what production actually hands the model."""
    result = run_single_tool_smoke_test(tool_count=1)
    return result.made_a_real_call
    # ^ True here says nothing about tool_count=22, which is what the
    #   agent will actually be given. The certification is real, and
    #   irrelevant.


# --- The fix ----------------------------------------------------------

def sound_certification(run_probe, production_tool_count: int,
                          probe_sizes: tuple[int, ...] = (1, 4, 8, 16)) -> dict:
    """Certifies a model only against the tool count it will actually run
    with in production — plus enough intermediate points to see where, if
    anywhere, it stops making real calls. A model that is fine at N=1 and
    silent at N=production is not "mostly working"; it is not working."""
    sizes_to_check = sorted(set(probe_sizes) | {production_tool_count})
    results = {n: run_probe(tool_count=n) for n in sizes_to_check}
    production_result = results[production_tool_count]
    return {
        "certified": production_result.made_a_real_call,
        "curve": {n: r.made_a_real_call for n, r in results.items()},
        "production_tool_count": production_tool_count,
    }


if __name__ == "__main__":
    # A deterministic stand-in for a real model call. Swap this for an
    # actual provider call to reproduce the measurement for real — the
    # shape of the result is what this pattern cares about, not the mock.
    _OBSERVED_CLIFF = 8  # calls stop succeeding at and above this count

    def probe(tool_count: int) -> ToolCallResult:
        return ToolCallResult(tool_count, made_a_real_call=tool_count < _OBSERVED_CLIFF)

    print("buggy_certification  :", "PASS" if buggy_certification(probe) else "FAIL",
          "(true, but only tells you about tool_count=1)")

    report = sound_certification(probe, production_tool_count=22)
    print("sound_certification  :", "PASS" if report["certified"] else "FAIL",
          "(correct: the production tool count is what actually matters)")
    print("curve                :", report["curve"])
