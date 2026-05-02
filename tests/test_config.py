import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile

import yaml

from config import get_llm


def test_get_llm_reads_yaml(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        cfg_file = Path(tmp) / "model_config.yaml"
        cfg = {
            "provider": "openai",
            "model": "test-model",
            "api_key_env": "TEST_API_KEY",
            "temperature": 0.5,
        }
        cfg_file.write_text(yaml.safe_dump(cfg), encoding="utf-8")

        monkeypatch.setenv("TEST_API_KEY", "fake-key")
        monkeypatch.setattr(
            "config.CONFIG_DIR", Path(tmp)
        )

        # ChatOpenAI should instantiate without network call
        llm = get_llm()
        assert llm.model_name == "test-model"
