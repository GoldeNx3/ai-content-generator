# Rola pliku: Punkt wejścia `python -m ai`: JSON z stdin, wynik JSON na stdout, logi wyłącznie na stderr.

import asyncio
import json
import logging
import sys

from ai.runtime import run


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(name)s %(message)s")
    try:
        request = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        response = {"ok": False, "error": {"code": "invalid_input", "message": str(exc), "retryable": False,
                                           "retry_after": None}, "calls": []}
    else:
        response = asyncio.run(run(request))
    sys.stdout.write(json.dumps(response, ensure_ascii=False, default=str))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
