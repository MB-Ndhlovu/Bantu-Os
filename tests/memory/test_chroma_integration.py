import pytest
import numpy as np

from bantu_os.memory.vector_store import ChromaVectorStore
from bantu_os.memory.memory import Memory


class DummyEmbeddings:
    """Always returns deterministic vectors for testing."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    async def embed(self, texts: list[str]) -> np.ndarray:
        # Deterministic: same text → same vector
        vecs = []
        for t in texts:
            v = np.zeros(self.dim, dtype=np.float32)
            for i, ch in enumerate(t):
                v[i % self.dim] += ord(ch)
            norm = np.linalg.norm(v)
            if norm > 0:
                v /= norm
            vecs.append(v)
        return np.stack(vecs)


@pytest.fixture
def chroma_store(tmp_path):
    store = ChromaVectorStore(
        path=str(tmp_path / "chroma"),
        collection="test_memory",
        dim=128,
    )
    yield store
    store.clear()


@pytest.fixture
def memory(chroma_store):
    return Memory(store=chroma_store, embeddings=DummyEmbeddings(dim=128), dim=128)


class TestChromaVectorStore:
    def test_add_and_search(self, chroma_store):
        vec = np.zeros(128, dtype=np.float32)
        vec[0] = 1.0
        uid = chroma_store.add(
            vector=vec, text="hello world", metadata={"type": "greeting"}
        )
        assert uid
        results = chroma_store.search(query_vector=vec, top_k=5)
        assert len(results) >= 1
        assert results[0]["text"] == "hello world"

    def test_add_multiple_and_search_topk(self, chroma_store):
        vectors = [np.zeros(128, dtype=np.float32) for _ in range(5)]
        texts = [
            "apple fruit",
            "banana fruit",
            "carrot vegetable",
            "date fruit",
            "egg food",
        ]
        for i, (v, t) in enumerate(zip(vectors, texts)):
            v[i] = 1.0
            chroma_store.add(vector=v, text=t, metadata={"idx": i})

        query = np.zeros(128, dtype=np.float32)
        query[0] = 1.0
        results = chroma_store.search(query_vector=query, top_k=3)
        assert len(results) <= 3
        assert results[0]["text"] == "apple fruit"

    def test_get_by_id(self, chroma_store):
        vec = np.ones(128, dtype=np.float32)
        uid = chroma_store.add(vector=vec, text="test record", metadata={"idx": 42})
        record = chroma_store.get(uid)
        assert record is not None
        assert record["text"] == "test record"

    def test_delete(self, chroma_store):
        vec = np.ones(128, dtype=np.float32)
        uid = chroma_store.add(vector=vec, text="to be deleted", metadata={})
        assert chroma_store.get(uid) is not None
        deleted = chroma_store.delete(uid)
        assert deleted is True

    def test_clear(self, chroma_store):
        vec = np.ones(128, dtype=np.float32)
        chroma_store.add(vector=vec, text="one", metadata={})
        chroma_store.add(vector=vec, text="two", metadata={})
        assert chroma_store.count() >= 2
        chroma_store.clear()
        assert chroma_store.count() == 0

    def test_fallback_when_chroma_unavailable(self, tmp_path, monkeypatch):
        import bantu_os.memory.vector_store as vs

        monkeypatch.setattr(vs, "HAS_CHROMADB", False)
        store = ChromaVectorStore(path=str(tmp_path / "chroma"), dim=128)
        assert store._coll is None
        assert hasattr(store, "_fallback")


class TestMemoryWithChroma:
    def test_store_and_retrieve(self, memory):
        id1 = memory.store_memory("I like chess", np.ones(128, dtype=np.float32) * 0.5)
        id2 = memory.store_memory(
            "chess is a strategy game", np.ones(128, dtype=np.float32) * 0.5
        )
        results = memory.store.search(
            query_vector=np.ones(128, dtype=np.float32) * 0.5, top_k=2
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_store_text_and_retrieve(self, memory):
        uid = await memory.store_text("The capital of France is Paris")
        assert uid
        results = await memory.retrieve_memory(
            "What is the capital of France?", top_k=1
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_store_text_requires_embeddings(self, memory, monkeypatch):
        memory.embeddings = None
        with pytest.raises(RuntimeError, match="Embeddings provider"):
            await memory.store_text("some text")
