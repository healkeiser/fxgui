"""Build fxgui's Rez package: the `fxgui` folder, as the wheel ships it."""

# Built-in
import os
import sys
from pathlib import Path

# What the wheel leaves out of `fxgui` (pyproject.toml, MANIFEST.in).
_NOT_SHIPPED = {".md", ".ai", ".pyc"}


def build(source_path: str, build_path: str, install_path: str) -> None:
    """Copy `fxgui` to `{install}/python/fxgui`, with its version metadata.

    `fxgui.__version__` reads `importlib.metadata`, so a dist-info naming
    the version goes beside it, as `lsd pip` installs one from the wheel.
    """
    # Imported here so tests load this file where `ls_rez` is not installed.
    from ls_rez.build import RezBuilder

    class Builder(RezBuilder):
        def should_ignore(self, path: Path) -> bool:
            return super().should_ignore(path) or path.suffix in _NOT_SHIPPED

    python = Path(install_path) / "python"
    Builder(
        source_path=str(Path(source_path) / "fxgui"),
        build_path=build_path,
        install_path=str(python / "fxgui"),
    ).build()
    version = os.environ["REZ_BUILD_PROJECT_VERSION"]
    info = python / f"fxgui-{version}.dist-info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: fxgui\nVersion: {version}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    # Rez passes `install` only when installing; a plain build stays local.
    if "install" not in sys.argv[1:]:
        sys.exit(0)
    build(
        source_path=os.environ["REZ_BUILD_SOURCE_PATH"],
        build_path=os.environ["REZ_BUILD_PATH"],
        install_path=os.environ["REZ_BUILD_INSTALL_PATH"],
    )
