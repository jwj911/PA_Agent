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
    EXPERIENCE_CURATION_REVIEW_SCHEMA,
    EXPERIENCE_CURATION_SCHEMA,
    curate_record,
    curate_record_by_id,
    export_record_review_catalog,
    scan_record_directory,
)


def _write_json(path: Path, value: dict[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(f"{target.suffix}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan")
    scan.add_argument("--records-dir", type=Path, required=True)

    export_review = subparsers.add_parser("export-review")
    export_review.add_argument("--records-dir", type=Path, required=True)
    export_review.add_argument("--output", type=Path, required=True)

    import_record = subparsers.add_parser("import-record")
    record_selector = import_record.add_mutually_exclusive_group(required=True)
    record_selector.add_argument("--record", type=Path)
    record_selector.add_argument("--record-id")
    import_record.add_argument("--records-dir", type=Path)
    import_record.add_argument("--experience-dir", type=Path, required=True)
    import_record.add_argument("--outcome", choices=("success", "failure"), required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            result = scan_record_directory(args.records_dir)
        elif args.command == "export-review":
            catalog = export_record_review_catalog(args.records_dir)
            _write_json(args.output, catalog)
            result = {
                "schema": EXPERIENCE_CURATION_REVIEW_SCHEMA,
                "eligible_count": catalog["eligible_count"],
                "output_file": Path(args.output).name,
            }
        else:
            api_key = (load_settings().provider.api_key or "").strip()
            if args.record_id is not None:
                if args.records_dir is None:
                    raise ValueError("--records-dir is required with --record-id")
                result = curate_record_by_id(
                    args.records_dir,
                    args.experience_dir,
                    record_id=args.record_id,
                    outcome=args.outcome,
                    sensitive_values=(api_key,),
                )
            else:
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
