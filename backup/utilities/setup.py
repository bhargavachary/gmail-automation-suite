#!/usr/bin/env python3
"""
Setup script for Gmail Automation Suite
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Read version from src/__init__.py
version = "3.0.0"
try:
    with open("src/__init__.py", "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("__version__"):
                version = line.split('"')[1]
                break
except FileNotFoundError:
    pass

setup(
    name="gmail-automation-suite",
    version=version,
    author="Gmail Automation Suite Team",
    author_email="team@gmail-automation-suite.com",
    description="Advanced Gmail automation with AI-powered email categorization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gmail-automation-suite",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "Topic :: Communications :: Email",
        "Topic :: Office/Business",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "isort>=5.0",
            "flake8>=3.8",
            "mypy>=0.812",
        ],
        "ml": [
            "torch>=1.9.0",
            "bertopic>=0.14.0",
            "umap-learn>=0.5.0",
            "hdbscan>=0.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "gmail-automation=gmail_automation:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.md", "*.txt"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/gmail-automation-suite/issues",
        "Source": "https://github.com/yourusername/gmail-automation-suite",
        "Documentation": "https://github.com/yourusername/gmail-automation-suite/blob/main/docs",
    },
    keywords=[
        "gmail",
        "automation",
        "email",
        "categorization",
        "ai",
        "machine learning",
        "productivity",
        "organization",
        "labels",
        "filters",
    ],
    zip_safe=False,
)