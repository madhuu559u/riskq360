from setuptools import setup, find_packages

setup(
    name="medinsight360",
    version="1.0.0",
    description="Unified Risk Adjustment + Quality Intelligence Platform",
    author="Next Era",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.34.0",
        "pydantic>=2.10.0",
        "pydantic-settings>=2.7.0",
        "sqlalchemy[asyncio]>=2.0.36",
        "asyncpg>=0.30.0",
        "openai>=1.58.0",
        "torch>=2.5.0",
        "transformers>=4.47.0",
        "scikit-learn>=1.6.0",
        "PyMuPDF>=1.25.0",
    ],
    entry_points={
        "console_scripts": [
            "medinsight360=scripts.run_chart:main",
        ],
    },
)
