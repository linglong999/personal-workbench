"""LLM 客户端抽象接口。"""

from openai import OpenAI

from workbench import usage


class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        price_in_per_m: float = 1.0,
        price_out_per_m: float = 2.0,
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        usage.set_prices(price_in_per_m, price_out_per_m)

    def complete(self, system: str, user: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        u = getattr(resp, "usage", None)
        if u is not None:
            usage.record_llm(
                self.model,
                system,
                user,
                getattr(u, "prompt_tokens", 0) or 0,
                getattr(u, "completion_tokens", 0) or 0,
            )
        content = resp.choices[0].message.content or ""
        return content
