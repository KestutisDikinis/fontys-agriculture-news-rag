from __future__ import annotations

from typing import TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class PromptBuilder:
    SYSTEM_PROMPT = """
You are Agri Watch, an assistant for farmers and agricultural advisors.

Answer using only the supplied retrieved context.

Clearly distinguish between:
- confirmed laws and policies;
- current or recently introduced rules;
- proposals, consultations, and rumors;
- future changes and upcoming deadlines.

Do not present proposals or consultations as confirmed law.

When the context does not contain enough information, say that the indexed
sources do not provide enough information. Do not invent dates, policies,
requirements, grants, or legal obligations.

Keep the answer direct and useful. Mention relevant dates and jurisdictions
when they are present in the context.
""".strip()

    def build_messages(
        self,
        question: str,
        context: str,
    ) -> list[ChatMessage]:
        user_message = f"""
Retrieved agriculture context:

--- BEGIN CONTEXT ---

{context}

--- END CONTEXT ---

Question:

{question}

Answer the question using the retrieved context.
""".strip()

        return [
            {
                "role": "system",
                "content": self.SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

    def build(self, question: str, context: str) -> str:
        """
        Retained for compatibility with any code or tests that expect
        PromptBuilder.build().
        """
        return f"""
{self.SYSTEM_PROMPT}

--- BEGIN CONTEXT ---

{context}

--- END CONTEXT ---

Question:

{question}

Answer:
""".strip()