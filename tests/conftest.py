import sys
from pathlib import Path
import pytest

# Ensure the project root (containing the bantu_os package) is on sys.path
THIS_FILE = Path(__file__).resolve()
for parent in [THIS_FILE.parent, *THIS_FILE.parents]:
    if (parent / "bantu_os").is_dir():
        root = parent
        break
else:
    root = THIS_FILE.parents[1]

if str(root) not in sys.path:
    sys.path.insert(0, str(root))


@pytest.fixture(autouse=True)
def stub_llm_provider(monkeypatch):
    """Stub provider creation globally to avoid real API and API key requirements.

    Kernel() constructs an LLM via LLMManager._build_provider -> OpenAIChatProvider,
    which raises if no API key is set. We replace it with a dummy provider.
    """
    from bantu_os.core.kernel.llm_manager import LLMManager

    class DummyProvider:
        def __init__(self, model: str, **kwargs):
            self.model = model

        async def generate(self, *, messages, temperature=0.7, max_tokens=None, **kwargs):
            # Default dummy behavior; individual tests typically patch kernel.llm.generate
            return {"text": "stub", "raw": {}}

    def _fake_build_provider(self, provider: str, model: str, **kwargs):
        return DummyProvider(model=model, **kwargs)

    monkeypatch.setattr(LLMManager, "_build_provider", _fake_build_provider, raising=True)
    yield
