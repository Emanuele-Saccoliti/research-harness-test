import importlib.util
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
