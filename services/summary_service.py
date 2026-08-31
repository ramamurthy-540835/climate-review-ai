from concurrent.futures import ThreadPoolExecutor

from services.llm_service import generate_content
from services.prompt_loader import load_prompt

summary_prompt = load_prompt("summary_prompt.txt")


def split_text(text: str, chunk_size: int = 6000, max_parts: int = 6):
    text = text[: chunk_size * max_parts]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end

    return chunks


def summarize_document(text: str):
    chunks = split_text(text)

    def summarize_part(item):
        i, chunk = item
        prompt = f"""
Summarize this part of the IPCC document clearly and concisely.

Part {i} of {len(chunks)}

Text:
{chunk}
"""
        return i, generate_content(prompt).text

    with ThreadPoolExecutor(max_workers=min(6, len(chunks))) as executor:
        partial_summaries = [text for _, text in sorted(executor.map(summarize_part, enumerate(chunks, start=1)))]

    combined_summary_text = "\n\n".join(partial_summaries)
    final_prompt = summary_prompt.replace("{text}", combined_summary_text)
    return generate_content(final_prompt).text