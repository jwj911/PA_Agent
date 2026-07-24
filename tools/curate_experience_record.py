"""Scan or explicitly curate local analysis records into experience cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pa_agent.config.settings import load_settings  # noqa: E402
from pa_agent.records.experience_curation import (  # noqa: E402
    EXPERIENCE_CURATION_SCHEMA,
    curate_record,
    scan_record_directory,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan")
    scan.add_argument("--records-dir", type=Path, required=True)

    import_record = subparsers.add_parser("import-record")
    import_record.add_argument("--record", type=Path, required=True)
    import_record.add_argument("--experience-dir", type=Path, required=True)
    import_record.add_argument("--outcome", choices=("success", "failure"), required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            result = scan_record_directory(args.records_dir)
        else:
            api_key = (load_settings().provider.api_key or "").strip()
            result = curate_record(
                args.record,
                args.experience_dir,
                outcome=args.outcome,
                sensitive_values=(api_key,),
            )
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "schema": EXPERIENCE_CURATION_SCHEMA,
                    "ok": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
