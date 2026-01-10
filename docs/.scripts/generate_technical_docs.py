"""Generate the technical documentation pages."""

# Build-in
from pathlib import Path

# Third-party
import mkdocs_gen_files


nav = mkdocs_gen_files.Nav()

root = Path(__file__).parent.parent.parent
src = root / "fxgui"

for path in sorted(src.rglob("*.py")):
    # Skip non-package directories (no __init__.py)
    if "ui" in path.parts:
        continue

    module_path = path.relative_to(root)
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("technical", doc_path)

    parts = tuple(module_path.with_suffix("").parts)

    # Skip __init__ files in navigation but still generate docs
    if parts[-1] == "__init__":
        parts = parts[:-1]
        if not parts:
            continue
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")

    # Skip private modules (starting with _) in navigation display
    # but use cleaned name for nav
    nav_parts = tuple(
        part.lstrip("_") if part.startswith("_") else part for part in parts
    )

    nav[nav_parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))

with mkdocs_gen_files.open("technical/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
