from pathlib import Path
import sys
import json
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.services.weekly_research import run
if __name__ == '__main__':
    output = os.getenv('WEEKLY_RESEARCH_RESULT_PATH', '')
    try:
        result = run()
    except Exception as exc:
        result = {"status": "runner_error", "error": type(exc).__name__}
    encoded = json.dumps(result, ensure_ascii=False, default=str)
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(encoded, encoding='utf-8')
    print(encoded, flush=True)
