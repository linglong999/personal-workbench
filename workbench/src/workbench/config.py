"""配置管理：从环境变量加载配置。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    vault_path: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    chroma_dir: str = ".data/chroma"
    embed_model: str = "default"
    llm_price_in_per_m: float = 1.0
    llm_price_out_per_m: float = 2.0

    @classmethod
    def from_env(cls, env=None):
        env = env or os.environ
        vault = env.get("VAULT_PATH")
        if not vault:
            raise ConfigError("VAULT_PATH 未设置")
        return cls(
            vault_path=vault,
            llm_base_url=env.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_api_key=env.get("LLM_API_KEY", ""),
            llm_model=env.get("LLM_MODEL", "gpt-4o-mini"),
            chroma_dir=env.get("CHROMA_DIR", ".data/chroma"),
            llm_price_in_per_m=float(env.get("LLM_PRICE_IN_PER_M", "1.0")),
            llm_price_out_per_m=float(env.get("LLM_PRICE_OUT_PER_M", "2.0")),
        )


def load_config(use_dotenv: bool = True) -> Config:
    if use_dotenv:
        load_dotenv()
    return Config.from_env()
