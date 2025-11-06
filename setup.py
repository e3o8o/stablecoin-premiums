"""Setup configuration for stablecoin_premiums package."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="stablecoin-premiums",
    version="0.1.0",
    author="Elem Oghenekaro",
    author_email="elem@elemoghenekaro.com",
    description="Utilities to fetch P2P stablecoin quotes and FX rates, then compute premiums/spreads across fiat markets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/e3o8o/stablecoin-premiums",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
        "notebooks": [
            "jupyter>=1.0.0",
            "pandas>=2.2.0",
            "numpy>=1.25.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "stablecoin-premiums=stablecoin_premiums.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
