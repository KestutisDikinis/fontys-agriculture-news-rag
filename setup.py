from setuptools import find_packages, setup

setup(
    name="agri-watch",
    version="0.1.0",
    description="Agriculture news and law-change scraper with classification, local RAG, and FastAPI UI.",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.110",
        "uvicorn[standard]>=0.27",
        "pydantic>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4",
            "ruff>=0.5",
        ]
    },
)
