import json
from pathlib import Path

WARNING_SIGNALS = [
    "do not use",
    "not finished",
    "draft",
    "deprecated",
    "do not distribute",
    "work in progress",
    "superseded"
]


def build_registry(documents: list[dict]) -> dict:
    registry = {}

    for doc in documents:
        filename = doc["filename"]
        content = doc["content"].lower()

        warning = None
        for signal in WARNING_SIGNALS:
            if signal in content:
                warning = signal
                break

        registry[filename] = {"warning": warning}

        if warning:
            print(f"⚠️  Warning detected in {filename}: '{warning}'")
        else:
            print(f"✅ {filename} — clean")

    return registry


def save_registry(registry: dict, output_path: str = "data/registry.json"):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    print(f"\nRegistry saved to {output_path}")


def load_registry(registry_path: str = "data/registry.json") -> dict:
    with open(registry_path, "r", encoding="utf-8") as f:
        return json.load(f)