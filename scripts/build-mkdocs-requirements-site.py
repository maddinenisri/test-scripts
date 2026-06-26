#!/usr/bin/env python3
"""Create a clean MkDocs project from generated ODM requirement Markdown."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


PLACEHOLDER = "Paste the chat LLM answer"


def titleize(value: str) -> str:
    value = value.replace("_", " ").replace("-", " ").replace(".gherkin", "")
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return " ".join(part.capitalize() for part in value.split()) or "Untitled"


def q(value: str) -> str:
    return json.dumps(value)


def rel(src_root: Path, path: Path) -> Path:
    return path.relative_to(src_root)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def copy_markdown(src: Path, dst: Path, heading: str | None = None) -> bool:
    text = src.read_text(encoding="utf-8", errors="replace").strip()
    if not text or PLACEHOLDER in text:
        return False
    if heading and not text.lstrip().startswith("#"):
        text = f"# {heading}\n\n{text}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text.rstrip() + "\n", encoding="utf-8")
    return True


def copy_tree(src_root: Path, dst_root: Path, rename_summary: bool = False) -> list[Path]:
    copied: list[Path] = []
    if not src_root.exists():
        return copied
    for src in sorted(src_root.rglob("*.md")):
        src_rel = rel(src_root, src)
        if rename_summary and src.name == "_summary.md":
            dst_rel = src_rel.parent / "index.md"
        else:
            dst_rel = src_rel
        dst = dst_root / dst_rel
        if copy_markdown(src, dst, titleize(dst.stem)):
            copied.append(dst)
    return copied


def link_for(docs_dir: Path, path: Path) -> str:
    return path.relative_to(docs_dir).as_posix()


def make_index(path: Path, title: str, docs_dir: Path, pages: list[Path]) -> None:
    lines = [f"# {title}", ""]
    if not pages:
        lines.append("_No completed Markdown responses found yet._")
    else:
        for page in pages:
            if page.name == "index.md":
                continue
            lines.append(f"- [{titleize(page.stem)}]({link_for(path.parent, page)})")
    write(path, "\n".join(lines))


def grouped_pages(root: Path) -> dict[Path, list[Path]]:
    groups: dict[Path, list[Path]] = {}
    if not root.exists():
        return groups
    for page in sorted(root.rglob("*.md")):
        if page.name == "index.md":
            continue
        groups.setdefault(page.parent, []).append(page)
    return groups


def write_directory_indexes(root: Path, section_title: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    dirs = {root}
    dirs.update(page.parent for page in root.rglob("*.md"))
    for directory in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        children = sorted(p for p in directory.iterdir() if p.is_dir())
        pages = sorted(p for p in directory.glob("*.md") if p.name != "index.md")
        title = section_title if directory == root else titleize(directory.name)
        lines = [f"# {title}", ""]
        for child in children:
            if (child / "index.md").exists():
                lines.append(f"- [{titleize(child.name)}]({child.name}/)")
        for page in pages:
            lines.append(f"- [{titleize(page.stem)}]({page.name})")
        if len(lines) == 2:
            lines.append("_No completed Markdown responses found yet._")
        write(directory / "index.md", "\n".join(lines))


def nav_for_dir(root: Path, docs_dir: Path) -> list[tuple[str, str | list]]:
    items: list[tuple[str, str | list]] = []
    if not root.exists():
        return items
    for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.is_dir():
            child_items = nav_for_dir(child, docs_dir)
            index = child / "index.md"
            if index.exists():
                child_items.insert(0, ("Overview", link_for(docs_dir, index)))
            if child_items:
                items.append((titleize(child.name), child_items))
        elif child.suffix == ".md" and child.name != "index.md":
            items.append((titleize(child.stem), link_for(docs_dir, child)))
    return items


def yaml_nav(items: list[tuple[str, str | list]], indent: int = 0) -> list[str]:
    lines: list[str] = []
    pad = " " * indent
    for title, value in items:
        if isinstance(value, list):
            lines.append(f"{pad}- {q(title)}:")
            lines.extend(yaml_nav(value, indent + 2))
        else:
            lines.append(f"{pad}- {q(title)}: {q(value)}")
    return lines


def build_site(source: Path, out: Path, site_name: str) -> None:
    responses = source / "responses"
    docs = out / "docs"
    if out.exists():
        shutil.rmtree(out)
    docs.mkdir(parents=True, exist_ok=True)

    operation_pages = copy_tree(responses / "operations", docs / "operations")
    folder_pages = copy_tree(responses / "folders", docs / "folders", rename_summary=True)
    rule_pages = copy_tree(responses / "rules", docs / "rules")

    write_directory_indexes(docs / "operations", "Operation Requirements")
    write_directory_indexes(docs / "folders", "Folder Summaries")
    write_directory_indexes(docs / "rules", "Rule Requirements")

    home = [
        f"# {site_name}",
        "",
        "This site is generated from ODM requirement Markdown responses.",
        "",
        "## Sections",
        "",
        "- [Operation Requirements](operations/)",
        "- [Folder Summaries](folders/)",
        "- [Rule Requirements](rules/)",
        "",
        "## Counts",
        "",
        f"- Operation pages: {len(operation_pages)}",
        f"- Folder summary pages: {len(folder_pages)}",
        f"- Rule pages: {len(rule_pages)}",
        "",
        "## Review Note",
        "",
        "Generated pages should preserve citations to ODM source files, UUIDs, operation contracts, and sample evidence.",
    ]
    write(docs / "index.md", "\n".join(home))

    nav: list[tuple[str, str | list]] = [
        ("Home", "index.md"),
        ("Operation Requirements", [("Overview", "operations/index.md"), *nav_for_dir(docs / "operations", docs)]),
        ("Folder Summaries", [("Overview", "folders/index.md"), *nav_for_dir(docs / "folders", docs)]),
        ("Rule Requirements", [("Overview", "rules/index.md"), *nav_for_dir(docs / "rules", docs)]),
    ]
    mkdocs = [
        f"site_name: {q(site_name)}",
        "docs_dir: docs",
        "site_dir: site",
        "theme:",
        "  name: readthedocs",
        "  navigation_depth: 4",
        "use_directory_urls: true",
        "nav:",
        *yaml_nav(nav, 2),
        "markdown_extensions:",
        "  - tables",
        "  - fenced_code",
        "  - toc:",
        "      permalink: true",
    ]
    write(out / "mkdocs.yml", "\n".join(mkdocs))
    write(
        out / "README.md",
        "\n".join(
            [
                f"# {site_name} MkDocs Project",
                "",
                "Run from this directory:",
                "",
                "```bash",
                "mkdocs serve",
                "mkdocs build",
                "```",
                "",
                "The static HTML is written to `site/` after `mkdocs build`.",
            ]
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("out/manual-llm-rule-requirements"))
    parser.add_argument("--out", type=Path, default=Path("out/requirements-mkdocs"))
    parser.add_argument("--site-name", default="ODM Requirements")
    args = parser.parse_args()
    build_site(args.source.resolve(), args.out.resolve(), args.site_name)
    print(f"Wrote MkDocs project to {args.out}")
    print(f"Run: cd {args.out} && mkdocs serve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
