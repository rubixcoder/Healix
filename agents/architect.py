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
                        "Analyze the error logs and the codebase context, then propose a fix. "
                        "If this is a retry attempt, carefully review the prior failure and propose a different approach."),
            ("user", "{user_prompt}")
        ])

    def plan_fix(self, state: dict[str, Any]) -> dict[str, str]:
        logs = state.get("logs", "")
        codebase_context = state.get("codebase_snapshot", "")
        retry_count = state.get("retry_count", 0)
        test_results = state.get("test_results", "")
        similar_incidents = state.get("similar_incidents", [])

        similar_context = ""
        if similar_incidents:
            similar_context = "Similar past incidents:\n"
            for incident in similar_incidents:
                similar_context += (
                    f"- [{incident.get('error_type')}] "
                    f"{incident.get('message')} in {incident.get('file_path')} "
                    f"({incident.get('service_name')})\n"
                )
            similar_context += "\n"

        # Build the user prompt dynamically based on retry attempt
        if retry_count == 0:
            # First attempt
            user_prompt = (
                f"Error logs:\n{logs}\n\n"
                f"Codebase context:\n{codebase_context}\n\n"
                f"{similar_context}"
                f"Return the corrected code and a short explanation."
            )
        else:
            # Retry attempt - include prior failure context
            user_prompt = (
                f"RETRY ATTEMPT {retry_count}\n\n"
                f"Error logs:\n{logs}\n\n"
                f"Codebase context:\n{codebase_context}\n\n"
                f"Previous attempt failed with:\n{test_results}\n\n"
                f"{similar_context}"
                f"The prior fix did not pass the tests. Please analyze why it failed and propose a different approach. "
                f"Consider:\n"
                f"1. What was the root cause of the error?\n"
                f"2. Why might the previous fix have failed?\n"
                f"3. What alternative solution should be tried?\n\n"
                f"Return the corrected code and a detailed explanation of your approach."
            )

        prompt_value = self.prompt.format_prompt(user_prompt=user_prompt)

        response = self.llm.invoke(prompt_value)
        if isinstance(response, AIMessage):
            suggested_fix = response.content
        else:
            suggested_fix = getattr(response, "content", str(response))

        return {
            "suggested_fix": suggested_fix.strip(),
        }
