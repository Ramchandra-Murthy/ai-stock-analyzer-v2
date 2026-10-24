from setuptools import find_packages, setup

setup(
    name="ai_stock_analyzer",
    version="1.0.0",
    author="Ramchandra-Murthy",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "yfinance",
        "pandas",
        "numpy",
        "plotly",
        "scikit-learn",
        "pandas_ta",
        "python-dotenv",
        "pydantic",
    ],
    entry_points={
        "console_scripts": [
            "analyze-stock=main:main",  # CLI command
        ]
    },
    python_requires=">=3.9",
)
