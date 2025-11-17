"""Setup script for SKU Recognition System"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="shopline-sku-recognition",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="SKU Recognition System using Grounding DINO + CLIP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/shopline-img-train",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'sku-download=scripts.download_sku_data:main',
            'sku-build-db=scripts.build_vector_db:main',
            'sku-inference=scripts.run_inference:main',
        ],
    },
)
