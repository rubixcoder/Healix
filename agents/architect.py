import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages.ai import AIMessage
from langchain_core.prompts import ChatPromptTemplate


class ArchitectAgent:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o", temperature: float = 0.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required to initialize ArchitectAgent. "
                "Set it in the environment or pass it explicitly."
            )

        self.llm = ChatOpenAI(model=model, temperature=temperature, api_key=self.api_key)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Site Reliability Engineer. "
                        "Analyze the error logs and the codebase context, then propose a fix."),
            ("user", "Error logs:\n{logs}\n\nCodebase context:\n{codebase_context}\n\n"
                     "Return the corrected code and a short explanation.")
        ])

    def plan_fix(self, state: dict[str, Any]) -> dict[str, str]:
        prompt_value = self.prompt.format_prompt(
            logs=state.get("logs", ""),
            codebase_context=state.get("codebase_snapshot", "")
        )

        response = self.llm.invoke(prompt_value)
        if isinstance(response, AIMessage):
            suggested_fix = response.content
        else:
            suggested_fix = getattr(response, "content", str(response))

        return {
            "suggested_fix": suggested_fix.strip(),
        }
