from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="pyside2_vfx_template",
    version="0.1.1",
    long_description=long_description,
    long_description_content_type="text/markdown",
    description="Custom Python classes and utilities tailored for PySide2 built UI, in VFX-oriented DCC applications.",
    author="Valentin Beaumont",
    author_email="valentin.onze@gmail.com",
    packages=find_packages(),
)
