"""Generate manual chat-LLM prompts per ODM rule file."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

from odm.operation_trace import OperationTrace, ResolvedRuleRef, TraceStep, trace_all
from odm.workspace import Workspace, WorkspaceFile, build_workspace


RULE_LANGUAGES = {"odm_brl", "odm_trl", "odm_dta", "odm_fct"}
RULE_SUFFIXES = {".brl", ".trl", ".dta", ".fct"}


def _dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj.dict()


def _slug(value: str) -> str:
    out = re.sub(r"[^A-Za-z0-9._/-]+", "_", value.strip())
    out = re.sub(r"_+", "_", out).strip("_")
    return out or "unnamed"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    _write(path, json.dumps(data, indent=2, sort_keys=True))


def _clear(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _rule_root(source: Path) -> Path:
    candidate = source / "rules"
    return candidate if candidate.is_dir() else source


def _rule_file_stem(source: Path, wf: WorkspaceFile) -> Path:
    try:
        rel = wf.path.resolve().relative_to(_rule_root(source).resolve())
    except ValueError:
        rel = Path(wf.rel_path)
    if rel.suffix.lower() in RULE_SUFFIXES:
        rel = rel.with_suffix("")
    return Path(_slug(rel.as_posix()))


def _flatten_rules(steps: Iterable[TraceStep]) -> list[ResolvedRuleRef]:
    out: list[ResolvedRuleRef] = []
    for step in steps:
        out.extend(step.rules)
        out.extend(_flatten_rules(step.substeps))
    return out


def _compact_contract(trace: OperationTrace) -> dict[str, Any]:
    return {
        "operation": trace.operation,
        "operation_uuid": trace.uuid,
        "operation_file": trace.file,
        "ruleset_name": trace.ruleset_name,
        "ruleflow": _dump(trace.ruleflow) if trace.ruleflow else None,
        "inputs": [_dump(v) for v in trace.inputs],
        "outputs": [_dump(v) for v in trace.outputs],
        "variable_sets": [_dump(vs) for vs in trace.variable_sets],
        "source_artifacts": _dump(trace.source_artifacts),
    }


def _operations_for_file(traces: list[OperationTrace], wf: WorkspaceFile) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for trace in traces:
        matches = [r for r in _flatten_rules(trace.steps) if r.file == wf.rel_path]
        if matches:
            out.append(
                {
                    "operation": trace.operation,
                    "operation_uuid": trace.uuid,
                    "ruleflow": _dump(trace.ruleflow) if trace.ruleflow else None,
                    "rule_refs": [_dump(m) for m in matches],
                }
            )
    return out


def _rule_file_fact(
    ws: Workspace,
    source: Path,
    traces: list[OperationTrace],
    wf: WorkspaceFile,
    max_source_chars: int,
) -> dict[str, Any]:
    text = wf.path.read_text(encoding="utf-8", errors="replace")
    truncated = False
    if len(text) > max_source_chars:
        text = text[:max_source_chars]
        truncated = True

    ofm = wf.metadata.odm_file_metadata
    records: list[dict[str, Any]] = []
    if ofm:
        for name, uuid, kind in wf.rule_records():
            record: dict[str, Any] = {
                "name": name,
                "uuid": uuid,
                "kind": kind,
                "file": wf.rel_path,
                "language": wf.language,
            }
            for rule in ofm.rules:
                if rule.name == name or rule.studio_uuid == uuid:
                    record.update(
                        {
                            "documentation": rule.documentation,
                            "bom_type_refs": list(rule.bom_type_refs),
                            "bom_type_keys": list(rule.bom_type_keys),
                        }
                    )
            for table in ofm.decision_tables:
                if table.name == name or table.studio_uuid == uuid:
                    record.update(
                        {
                            "documentation": table.documentation,
                            "execution": _dump(table.execution) if table.execution else None,
                            "preconditions": table.preconditions,
                            "precondition_statements": list(table.precondition_statements),
                            "bom_type_refs": list(table.bom_type_refs),
                            "bom_type_keys": list(table.bom_type_keys),
                            "rows": [_dump(row) for row in ofm.decision_table_rows],
                        }
                    )
            records.append(record)

    operation_refs = _operations_for_file(traces, wf)
    op_names = {item["operation"] for item in operation_refs}
    return {
        "schema_version": "odm-rule-file-prompt/v1",
        "file": wf.rel_path,
        "folder": _rule_file_stem(source, wf).parent.as_posix(),
        "project": wf.project_dir.name if wf.project_dir else None,
        "language": wf.language,
        "rules": records,
        "operation_refs": operation_refs,
        "operation_contexts": [_compact_contract(t) for t in traces if t.operation in op_names],
        "source": {
            "file": wf.rel_path,
            "truncated": truncated,
            "text": text,
        },
        "workspace_warnings": list(ws.warnings),
    }


def _render_prompt(fact: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# ODM Rule File Requirement Prompt: {fact['file']}",
            "",
            "You are analyzing one IBM ODM rule source file.",
            "",
            "Use only the supplied facts and source. Do not invent behavior.",
            "Every generated requirement must cite the source file and rule UUID when present.",
            "Mark unclear rationale as `Inferred - confirm`.",
            "",
            "Produce Markdown with these sections:",
            "",
            "1. Rule File Summary",
            "2. Rule-Level Requirements",
            "3. Inputs And Conditions",
            "4. Outputs And Actions",
            "5. Operation Impact",
            "6. Gherkin Candidates",
            "7. Open Questions",
            "8. Citations",
            "",
            "If the file contains multiple rules or decision-table rows, keep the requirements separated by rule/row.",
            "",
            "## Parser Facts",
            "",
            "```json",
            json.dumps(fact, indent=2, sort_keys=True),
            "```",
        ]
    )


def generate_rule_file_prompts(source: Path, out: Path, max_source_chars: int = 20000) -> int:
    ws = build_workspace(source)
    traces = trace_all(ws)

    _clear(out / "facts" / "rules")
    _clear(out / "prompts" / "rules")
    (out / "responses" / "rules").mkdir(parents=True, exist_ok=True)

    rule_files = [wf for wf in sorted(ws.files, key=lambda item: item.rel_path) if wf.language in RULE_LANGUAGES]
    index = [
        "# ODM Rule File Prompts",
        "",
        "Copy each prompt into your chat LLM. Paste the answer into the matching response file.",
        "",
    ]

    for wf in rule_files:
        stem = _rule_file_stem(source, wf)
        fact = _rule_file_fact(ws, source, traces, wf, max_source_chars)
        fact_path = out / "facts" / "rules" / stem.with_suffix(".json")
        prompt_path = out / "prompts" / "rules" / stem.with_suffix(".prompt.md")
        response_path = out / "responses" / "rules" / stem.with_suffix(".md")
        _write_json(fact_path, fact)
        _write(prompt_path, _render_prompt(fact))
        if not response_path.exists():
            _write(
                response_path,
                "\n".join(
                    [
                        f"# LLM Response: {wf.rel_path}",
                        "",
                        "Paste the chat LLM answer for the matching rule-file prompt here.",
                    ]
                ),
            )
        index.append(f"- `{_rel(out, prompt_path)}` -> `{_rel(out, response_path)}`")

    _write(out / "prompts" / "rules" / "index.md", "\n".join(index))
    return len(rule_files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odm-rule-prompts",
        description="Generate one manual chat-LLM Markdown prompt per ODM rule file.",
    )
    parser.add_argument("source", type=Path, help="ODM project or workspace root directory")
    parser.add_argument("-o", "--out", type=Path, default=Path("out/rule-prompts"))
    parser.add_argument("--max-source-chars", type=int, default=20000)
    args = parser.parse_args(argv)

    count = generate_rule_file_prompts(args.source.resolve(), args.out.resolve(), args.max_source_chars)
    print(f"Wrote {count} rule-file prompt(s) to {args.out.resolve()}")
    print(f"Start with {args.out.resolve() / 'prompts' / 'rules' / 'index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
