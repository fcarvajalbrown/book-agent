import os
from pathlib import Path

import yaml
from langchain_core.language_models.chat_models import BaseChatModel

CONFIG_DIR = Path(__file__).parent


def get_llm() -> BaseChatModel:
    # load model config and return an instantiated chat model
    cfg_path = CONFIG_DIR / "model_config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    provider = cfg.get("provider", "openai")
    model = cfg.get("model", "gpt-4o-mini")
    temperature = cfg.get("temperature", 0.0)
    api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
    base_url = cfg.get("base_url")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        kwargs = {"model": model, "temperature": temperature, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError("langchain-anthropic not installed") from exc
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )

    raise ValueError(f"unknown provider: {provider}")
