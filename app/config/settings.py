from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Agri Watch")
    environment: str = os.getenv("APP_ENV", "development")

    data_dir: Path = Path(
        os.getenv(
            "DATA_DIR",
            PROJECT_ROOT / "data",
        )
    )

    database_path: Path = Path(
        os.getenv(
            "DATABASE_PATH",
            PROJECT_ROOT / "data" / "agri_watch.sqlite3",
        )
    )

    rss_timeout_seconds: int = int(
        os.getenv("RSS_TIMEOUT_SECONDS", "45")
    )

    rag_top_k: int = int(
        os.getenv("RAG_TOP_K", "5")
    )

    # Local GGUF language model.
    llm_model_path: Path = Path(
        os.getenv(
            "LLM_MODEL_PATH",
            PROJECT_ROOT
            / "models"
            / "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        )
    )

    llm_context_size: int = int(
        os.getenv("LLM_CONTEXT_SIZE", "4096")
    )

    llm_max_tokens: int = int(
        os.getenv("LLM_MAX_TOKENS", "512")
    )

    llm_temperature: float = float(
        os.getenv("LLM_TEMPERATURE", "0.1")
    )

    # Use 0 for CPU-only.
    # You can set -1 through an environment variable when GPU/Metal
    # acceleration is correctly installed.
    llm_gpu_layers: int = int(
        os.getenv("LLM_GPU_LAYERS", "0")
    )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.llm_model_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()