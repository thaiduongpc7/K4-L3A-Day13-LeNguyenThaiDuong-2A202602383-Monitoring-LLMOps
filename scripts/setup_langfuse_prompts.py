from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from langfuse import get_client


PROMPT_V1 = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
PROMPT_V2 = (
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer with a concise incident-investigation style response."
)


def prompt_name() -> str:
    return os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")


def init_prompts() -> None:
    client = get_client()
    name = prompt_name()
    first = client.create_prompt(
        name=name,
        prompt=PROMPT_V1,
        type="text",
        labels=["baseline", "production"],
        tags=["day13", "k4-l3a"],
        commit_message="baseline prompt for Day 13 lab",
    )
    second = client.create_prompt(
        name=name,
        prompt=PROMPT_V2,
        type="text",
        labels=["candidate"],
        tags=["day13", "k4-l3a"],
        commit_message="candidate prompt for rollback evidence",
    )
    print(f"Created prompt {name} baseline/production version={first.version}")
    print(f"Created prompt {name} candidate version={second.version}")


def promote(version: int) -> None:
    client = get_client()
    name = prompt_name()
    client.update_prompt(name=name, version=version, new_labels=["candidate", "production"])
    print(f"Promoted prompt {name} version={version} to production")


def rollback(version: int) -> None:
    client = get_client()
    name = prompt_name()
    client.update_prompt(name=name, version=version, new_labels=["baseline", "production"])
    print(f"Rolled back prompt {name} production to version={version}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Create and relabel Langfuse prompt versions.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create baseline/production and candidate prompt versions.")
    promote_parser = subparsers.add_parser("promote", help="Move production to a candidate version.")
    promote_parser.add_argument("--version", type=int, required=True)
    rollback_parser = subparsers.add_parser("rollback", help="Move production back to a baseline version.")
    rollback_parser.add_argument("--version", type=int, required=True)
    args = parser.parse_args()

    if args.command == "init":
        init_prompts()
    elif args.command == "promote":
        promote(args.version)
    elif args.command == "rollback":
        rollback(args.version)


if __name__ == "__main__":
    main()
