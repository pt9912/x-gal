"""
Setup configuration for GAL (Gateway Abstraction Layer)
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from VERSION file
version = Path("VERSION").read_text().strip()

# Read long description from README
long_description = Path("README.md").read_text(encoding="utf-8")

setup(
    name="gal-gateway",
    version=version,
    author="Dietmar Burkard",
    author_email="",
    description="Gateway Abstraction Layer - Provider-agnostic API Gateway configuration system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pt9912/x-gal",
    project_urls={
        "Bug Tracker": "https://github.com/pt9912/x-gal/issues",
        "Documentation": "https://github.com/pt9912/x-gal/blob/main/README.md",
        "Source Code": "https://github.com/pt9912/x-gal",
        "Changelog": "https://github.com/pt9912/x-gal/blob/main/CHANGELOG.md",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Code Generators",
        "Topic :: System :: Networking",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Typing :: Typed",
        "Framework :: AsyncIO",
    ],
    keywords=[
        "api-gateway",
        "envoy",
        "kong",
        "apisix",
        "traefik",
        "gateway",
        "configuration",
        "abstraction",
        "devops",
        "infrastructure",
        "rate-limiting",
        "authentication",
        "cors",
        "circuit-breaker",
        "health-checks",
        "load-balancing",
        "jwt",
        "security",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click>=8.1.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
            "isort>=5.13.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "gal=gal.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "gal": ["py.typed"],
    },
    zip_safe=False,
)
