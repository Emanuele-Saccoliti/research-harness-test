#!/usr/bin/env python3
"""Little research harness driven by Codex CLI."""

import argparse
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BASELINE = '''def optimize(start, steps):
    x, y = start
    for _ in range(steps):
        x -= 0.001 * 2 * (x - 1)
        y -= 0.001 * 200 * (y + 2)
    return x, y
'''

BENCHMARK = '''import importlib.util
import json
import math
import sys
from pathlib import Path

path = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("candidate_module", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.optimize((10.0, 10.0), 100)
if not isinstance(result, (tuple, list)) or len(result) != 2:
    raise ValueError("optimize must return two numbers")
x, y = map(float, result)
score = (x - 1) ** 2 + 100 * (y + 2) ** 2
if not math.isfinite(score):
    raise ValueError("non-finite score")
print(json.dumps({"score": score, "result": [x, y]}))
'''

SCHEMA = {
    "type": "object",
    "properties": {"hypotheses": {"type": "array", "minItems": 2, "maxItems": 3,
        "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "change": {"type": "string"},
            "rationale": {"type": "string"}},
            "required": ["title", "change", "rationale"], "additionalProperties": False}}},
    "required": ["hypotheses"], "additionalProperties": False,
}


def write_once(path, content):
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def setup(repo):
    repo.mkdir(parents=True, exist_ok=True)
    write_once(repo / "baseline.py", BASELINE)
    write_once(repo / "candidate.py", BASELINE)
    write_once(repo / "benchmark.py", BENCHMARK)
    write_once(repo / "proposal_schema.json", json.dumps(SCHEMA, indent=2))
    (repo / "runs").mkdir(exist_ok=True)


def score(repo, filename):
    proc = subprocess.run([sys.executable, "-I", "benchmark.py", filename],
                          cwd=repo, text=True, capture_output=True, timeout=30, check=True)
    return json.loads(proc.stdout.strip())


def codex(repo, prompt, output, schema=None):
    # In current Codex CLI versions, --approve-for-me already selects the
    # workspace-write sandbox and cannot be combined with --sandbox.
    command = ["codex", "exec", "--cd", str(repo), "--approve-for-me",
               "--output-last-message", str(output)]
    if schema:
        command += ["--output-schema", str(schema)]
    command.append(prompt)
    log_path = repo / "runs" / (output.stem + ".log")
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(command, cwd=repo, stdin=subprocess.DEVNULL,
                              stdout=log, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        details = log_path.read_text(encoding="utf-8").strip()
        raise RuntimeError(
            f"Codex exited with status {proc.returncode}.\n{details}"
        )
    return output.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("./harness_demo"))
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    setup(repo)
    baseline = score(repo, "baseline.py")
    print(f"Repository: {repo}\nBaseline score (lower is better): {baseline['score']:.8g}", flush=True)
    if shutil.which("codex") is None:
        parser.error("Codex CLI missing: install it and run `codex login` first")

    proposal_text = codex(repo,
        "Read baseline.py and benchmark.py. Propose 2 or 3 distinct numerical "
        "hypotheses to reduce the fixed benchmark score. Explain each briefly. "
        "This is proposal-only: do not edit files, run experiments, or install packages. "
        "Return only JSON matching the requested schema.",
        repo / "runs" / "proposals.json", repo / "proposal_schema.json")
    hypotheses = json.loads(proposal_text)["hypotheses"]
    for i, item in enumerate(hypotheses, 1):
        print(f"\n{i}. {item['title']}\n   {item['change']}\n   {item['rationale']}")
    while True:
        choice = input("\nChoose hypothesis number (or q to stop): ").strip()
        if choice.lower() == "q":
            return
        if choice.isdigit() and 1 <= int(choice) <= len(hypotheses):
            break
    selected = hypotheses[int(choice) - 1]
    before = (repo / "candidate.py").read_text(encoding="utf-8")
    try:
        summary = codex(repo,
            "Implement ONLY this selected hypothesis in candidate.py: "
            + json.dumps(selected) + ". Keep optimize(start, steps) compatible with "
            "benchmark.py. You may run code and install dependencies if useful. "
            "Do not edit baseline.py or benchmark.py. Summarize the change.",
            repo / "runs" / "implementation.txt")
        # Detect accidental benchmark changes even if the agent ignores the instruction.
        if (repo / "baseline.py").read_text(encoding="utf-8") != BASELINE or \
           (repo / "benchmark.py").read_text(encoding="utf-8") != BENCHMARK:
            raise RuntimeError("Baseline or benchmark changed; result rejected")
        candidate = score(repo, "candidate.py")
        improvement = baseline["score"] - candidate["score"]
        record = {"utc": datetime.now(timezone.utc).isoformat(),
                  "hypothesis": selected, "baseline": baseline, "candidate": candidate,
                  "improvement": improvement, "improved": improvement > 0,
                  "candidate_before": before,
                  "candidate_after": (repo / "candidate.py").read_text(encoding="utf-8"),
                  "codex_summary": summary}
        report = repo / "runs" / "result.json"
        report.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"\nCandidate score: {candidate['score']:.8g}")
        print(f"Improvement: {improvement:.8g}\nReport: {report}")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, RuntimeError) as exc:
        print(f"Experiment failed: {exc}. See {repo / 'runs'}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
