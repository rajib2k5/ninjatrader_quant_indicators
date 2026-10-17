"""Minimal packaging so `python -I -m qibt.cli` can import qibt (python -I ignores the current
directory). Install once, editable, from the repo root:

    python -s -m pip install --no-deps --no-build-isolation -e backtest
"""
from setuptools import setup

setup(
    name="qibt",
    version="0.1.0",
    description="Pre-registered backtest of the QI indicator classifications (educational research only)",
    packages=["qibt"],
    python_requires=">=3.9",
)
