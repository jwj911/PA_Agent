"""Export sanitized experience labels or generate an offline evaluation report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pa_agent.records.experience_eval import dump_dataset, dump_split  # noqa: E402
from pa_agent.records.experience_eval_pipeline import (  # noqa: E402
    evaluate_annotated_experience,
    export_annotation_template,
)

SALT_ENV = "PA_AGENT_EXPERIENCE_EVAL_SALT"


def _write_json(path: Path, value: dict[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid experience annotation JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("experience annotations must be a JSON object")
    return value


def _salt_from_environment() -> str:
    salt = os.environ.get(SALT_ENV, "")
    if not salt:
        raise ValueError(f"set {SALT_ENV} before running experience evaluation")
    return salt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export-labels")
    export.add_argument("--experience-dir", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--experience-dir", type=Path, required=True)
    evaluate.add_argument("--annotations", type=Path, required=True)
    evaluate.add_argument("--output-dir", type=Path, required=True)
    evaluate.add_argument("--evaluation-fraction", type=float, default=0.2)
    evaluate.add_argument("--k", type=int, default=3)

    args = parser.parse_args(argv)
    try:
        salt = _salt_from_environment()
        if args.command == "export-labels":
            template = export_annotation_template(args.experience_dir, salt=salt)
            _write_json(args.output, template)
            summary = {
                "schema": template["schema"],
                "case_count": len(template["cases"]),
                "output_file": Path(args.output).name,
            }
        else:
            annotations = _load_json(args.annotations)
            dataset, split, report = evaluate_annotated_experience(
                args.experience_dir,
                annotations,
                salt=salt,
                evaluation_fraction=args.evaluation_fraction,
                k=args.k,
            )
            output_dir = Path(args.output_dir)
            dump_dataset(output_dir / "dataset.json", dataset)
            dump_split(output_dir / "split.json", split)
            _write_json(output_dir / "report.json", report)
            summary = {
                "schema": report["schema"],
                "case_count": report["case_count"],
                "evaluation_case_count": report["evaluation_case_count"],
                "output_files": ["dataset.json", "split.json", "report.json"],
            }
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "schema": "pa-agent.experience-eval-command.v1",
                    "ok": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
