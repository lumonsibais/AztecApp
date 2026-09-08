import sys
from pathlib import Path
from aztec_crew.crew import AztecCrew

SPRINT = "sprint1"


def run():
    Path(f"output/{SPRINT}").mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"🚀 AztecApp Backend Crew — {SPRINT}")
    print("🤖 Modelo: Qwen2.5-Coder 3B local via llama.cpp")
    print("=" * 60 + "\n")

    try:
        result = AztecCrew().crew().kickoff()
        print(f"\n✅ Completado. Revisa output/{SPRINT}/")
        return result
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
