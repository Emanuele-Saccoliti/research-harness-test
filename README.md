# Research Harness

A minimal experimental harness that uses the locally authenticated Codex CLI to run a small proposal-implementation loop.

The script creates a tiny demo repository, defines a baseline optimizer, asks Codex to propose numerical hypotheses for improving a fixed benchmark score, lets the user choose one hypothesis, applies it to a candidate implementation, and records the resulting score.

## Files

- `research_harness.py` - command-line driver for the research loop.
- `harness_demo/baseline.py` - baseline implementation used by the demo.
- `harness_demo/benchmark.py` - fixed benchmark used to score candidates.
- `harness_demo/proposal_schema.json` - JSON schema for Codex proposals.
- `README.md` - brief project description.
- `LICENSE` - MIT license.

Generated demo files, run logs, and results are created locally when the script runs.

## Requirements

- Python 3.12 or compatible Python 3 version.
- Codex CLI installed and authenticated locally.

## Usage

```bash
python research_harness.py
```

The script will print the baseline score, ask Codex for candidate hypotheses, prompt you to choose one, and then evaluate the resulting candidate implementation.

## License

MIT
