"""PyPI setup script."""

# Built-in
from setuptools import setup, find_packages
from pathlib import Path

# Metadata
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


# Add `README.md` as project long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="fxgui",
    version="2.2.1",
    long_description=long_description,
    long_description_content_type="text/markdown",
    description="Custom Python classes and utilities tailored for Qt built UI, in VFX-oriented DCC applications.",
    author="Valentin Beaumont",
    author_email="valentin.onze@gmail.com",
    packages=find_packages(),
    install_requires=[
        "qtpy",
        "PySide2",
    ],
    include_package_data=True,
)
