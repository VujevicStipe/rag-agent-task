import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import Orchestrator

TEST_QUESTIONS = [
    "What is the deadline for submitting expense claims?",
    "Who must approve international business travel before booking?",
    "Create an onboarding checklist for a new employee.",
    "Can a new employee automatically receive production access during onboarding?",
    "What should happen to system access and company equipment when an employee leaves the company?",
    "Where should company or client data be stored?",
    "What should an employee do if they accidentally send confidential client data to the wrong external email address?",
    "What should be done if zulmar fragmentation is detected according to the Zulmar Fragmentation Protocol?",
    "Summarize the Krzth Monolithic Reference document.",
    "What procedures are described in the Symbolic Operational Reference document?",
]


def run_evaluation():
    orchestrator = Orchestrator()
    results = []

    print("=" * 60)
    print(" EVALUATION — 10 TEST QUESTIONS")
    print("=" * 60)

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[{i}/10] {question[:60]}...")

        try:
            context = orchestrator.run(question)

            result = {
                "question": question,
                "query_type": context.query_type,
                "is_answerable": context.is_answerable,
                "sources": context.sources,
                "flagged_sources": context.flagged_sources,
                "answer": context.answer,
                "status": "OK"
            }

            print(f"  Type:       {context.query_type}")
            print(f"  Answerable: {context.is_answerable}")
            print(f"  Sources:    {len(context.sources)}")
            if context.flagged_sources:
                print(f"  Flagged:    {len(context.flagged_sources)}")
            print(f"  Answer:     {context.answer[:100].strip()}...")

        except Exception as e:
            result = {
                "question": question,
                "status": "ERROR",
                "error": str(e)
            }
            print(f"  ERROR: {e}")

        results.append(result)
        time.sleep(3)

    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)

    ok = sum(1 for r in results if r["status"] == "OK")
    answerable = sum(1 for r in results if r.get("is_answerable"))
    not_found = sum(1 for r in results if r["status"] == "OK" and not r.get("is_answerable"))
    flagged = sum(1 for r in results if r.get("flagged_sources"))
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"  Total:        {len(results)}")
    print(f"  OK:           {ok}")
    print(f"  Answerable:   {answerable}")
    print(f"  Not found:    {not_found}")
    print(f"  With flagged: {flagged}")
    print(f"  Errors:       {errors}")

    return results


if __name__ == "__main__":
    run_evaluation()