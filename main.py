import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import Orchestrator


def print_results(context):
    print("\n" + "=" * 50)
    print(" STEPS")
    print("=" * 50)

    for i, step in enumerate(context.steps, 1):
        print(f"\n[{i}] {step.agent}")
        for key, value in step.details.items():
            print(f"    → {key}: {value}")

    print("\n" + "=" * 50)
    print(" SOURCES")
    print("=" * 50)

    if context.sources:
        for source in context.sources:
            print(f"  📄 {source}")
    else:
        print("  No sources found.")

    print("\n" + "=" * 50)
    print(" ANSWER")
    print("=" * 50)
    print(f"\n{context.answer}\n")


def main():
    orchestrator = Orchestrator()

    print("\n" + "=" * 50)
    print(" Company Knowledge Assistant")
    print(" Type 'exit' to quit")
    print("=" * 50)

    while True:
        print()
        query = input("Question: ").strip()

        if not query:
            continue

        if query.lower() == "exit":
            print("Goodbye.")
            break

        print("\nProcessing...")
        context = orchestrator.run(query)
        print_results(context)


if __name__ == "__main__":
    main()