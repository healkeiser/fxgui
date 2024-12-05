"""PyPI setup script."""

# Built-in
from pathlib import Path
from setuptools import setup, find_packages

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


# Add `README.md` as project long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="fxgui",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    description="Custom Python classes and utilities tailored for Qt built UI, in VFX-oriented DCC applications.",
    url="https://github.com/healkeiser/fxgui",
    author="Valentin Beaumont",
    author_email="valentin.onze@gmail.com",
    license="MIT",
    keywords="Qt PySide2 VFX DCC UI",
    packages=find_packages(),
    install_requires=["QtPy==2.4.2", "QtAwesome==1.3.1"],
    include_package_data=True,
    project_urls={
        "Documentation": "https://healkeiser.github.io/fxgui",
        "GitHub": "https://github.com/healkeiser/fxgui",
        "Changelog": "https://github.com/healkeiser/fxgui/blob/main/CHANGELOG.md",
        "Source": "https://github.com/healkeiser/fxgui",
        "Funding": "https://github.com/sponsors/healkeiser",
    },
)
