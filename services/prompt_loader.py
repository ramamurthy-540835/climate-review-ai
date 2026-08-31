from pathlib import Path

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    """
    Load a prompt template from the prompts folder.
    """
    path = PROMPT_DIR / filename

    with open(path, "r", encoding="utf-8") as file:
        return file.read()