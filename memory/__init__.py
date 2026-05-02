import pickle
from collections import defaultdict
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver


def _nested_defaultdict():
    return defaultdict(dict)


class FileSaver(InMemorySaver):
    """InMemorySaver that pickles checkpoints to disk after each write."""

    def __init__(self, dirpath: str = "memory/checkpoints") -> None:
        super().__init__()
        self._dir = Path(dirpath)
        self._dir.mkdir(parents=True, exist_ok=True)
        self.storage = defaultdict(_nested_defaultdict)
        self.writes = defaultdict(dict)
        self.blobs = {}
        self._load()

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        with open(self._state_file, "rb") as f:
            data = pickle.load(f)
        self.storage = self._restore_storage(data.get("storage", {}))
        self.writes = self._restore_writes(data.get("writes", {}))
        self.blobs = data.get("blobs", {})

    @property
    def _state_file(self) -> Path:
        return self._dir / "state.pkl"

    def _restore_storage(self, data):
        storage = defaultdict(_nested_defaultdict)
        for thread_id, ns_data in data.items():
            ns_dict = defaultdict(dict)
            for ns, ckpts in ns_data.items():
                ns_dict[ns] = dict(ckpts)
            storage[thread_id] = ns_dict
        return storage

    def _restore_writes(self, data):
        writes = defaultdict(dict)
        for key, value in data.items():
            writes[key] = dict(value)
        return writes

    def _persist(self) -> None:
        with open(self._state_file, "wb") as f:
            pickle.dump(
                {
                    "storage": dict(self.storage),
                    "writes": dict(self.writes),
                    "blobs": self.blobs,
                },
                f,
            )

    def put(self, config, checkpoint, metadata, new_versions):
        result = super().put(config, checkpoint, metadata, new_versions)
        self._persist()
        return result

    def put_writes(self, config, writes, task_id, task_path=""):
        super().put_writes(config, writes, task_id, task_path)
        self._persist()
