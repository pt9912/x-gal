from setuptools import setup, find_packages

setup(
    name="gal",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
        "Jinja2>=3.1.0",
        "click>=8.1.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "gal=gal.cli:main",
        ],
    },
    author="Your Name",
    description="Gateway Abstraction Layer - Provider-agnostic API Gateway configuration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
)
