from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, ClassVar, cast

from llama_cpp import Llama

from app.config import settings
from app.llm.prompt_builder import PromptBuilder


class LLMConfigurationError(RuntimeError):
    """Raised when the local LLM is not configured correctly."""


class LLMGenerationError(RuntimeError):
    """Raised when the local LLM cannot generate a valid response."""


class LLMClient:
    """
    Local GGUF language-model client backed by llama-cpp-python.

    The underlying model is stored as a process-wide singleton because loading
    a GGUF model is expensive. FastAPI may create LocalRAG and LLMClient
    instances for multiple requests, but the model itself should only be
    loaded once per Python process.
    """

    _model: ClassVar[Llama | None] = None
    _model_lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        model_path: str | Path | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.model_path = Path(
            model_path or settings.llm_model_path
        ).expanduser().resolve()

        self.prompt_builder = prompt_builder or PromptBuilder()

    def answer_from_context(
        self,
        question: str,
        context: str,
    ) -> str:
        question = question.strip()
        context = context.strip()

        if not question:
            raise ValueError("Question cannot be empty.")

        if not context:
            return (
                "I could not find relevant information in the indexed "
                "agriculture sources."
            )

        model = self._get_model()

        messages = self.prompt_builder.build_messages(
            question=question,
            context=context,
        )

        try:
            response = model.create_chat_completion(
                messages=cast(Any, messages),
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                top_p=0.9,
                repeat_penalty=1.1,
                stream=False,
            )
        except Exception as exc:
            raise LLMGenerationError(
                f"Local LLM generation failed: {exc}"
            ) from exc

        answer = self._extract_answer(response)

        if not answer:
            return (
                "The local model did not produce an answer from the "
                "retrieved agriculture context."
            )

        return answer

    def _get_model(self) -> Llama:
        """
        Load the model once and reuse it for all LLMClient instances.
        """
        if LLMClient._model is not None:
            return LLMClient._model

        with LLMClient._model_lock:
            if LLMClient._model is not None:
                return LLMClient._model

            if not self.model_path.exists():
                raise LLMConfigurationError(
                    "Local GGUF model was not found at: "
                    f"{self.model_path}"
                )

            if not self.model_path.is_file():
                raise LLMConfigurationError(
                    "Configured LLM path is not a file: "
                    f"{self.model_path}"
                )

            try:
                LLMClient._model = Llama(
                    model_path=str(self.model_path),
                    n_ctx=settings.llm_context_size,
                    n_gpu_layers=settings.llm_gpu_layers,
                    verbose=False,
                )
            except Exception as exc:
                raise LLMConfigurationError(
                    "Could not load the local GGUF model from "
                    f"{self.model_path}: {exc}"
                ) from exc

            return LLMClient._model

    @staticmethod
    def _extract_answer(response: Any) -> str:
        """
        Extract content from llama-cpp-python's chat-completion response.
        """
        if not isinstance(response, dict):
            return ""

        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""

        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()

        # Defensive fallback for completion-style responses.
        text = first_choice.get("text")
        if isinstance(text, str):
            return text.strip()

        return ""