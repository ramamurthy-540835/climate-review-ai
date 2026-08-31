from google import genai

from config import GEMINI_MODEL, GENAI_LOCATION, PROJECT_ID
from services.prompt_loader import load_prompt
from services.retrieval_service import retrieve_context

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=GENAI_LOCATION,
)

qa_prompt = load_prompt("qa_prompt.txt")

def generate_content(prompt: str):
    return client.models.generate_content(model=GEMINI_MODEL, contents=prompt)


def build_context(contexts):
    context_text = ""

    for i, item in enumerate(contexts, start=1):
        page = item["page_start"]
        if item["page_end"] != page:
            page = f"{page}-{item['page_end']}"
        context_text += (
            f"\nSource {i}\n"
            f"Document: {item['document']}\n"
            f"Page: {page}\n"
            f"Chunk: {item['chunk']}\n\n"
            f"{item['content']}\n\n"
        )

    return context_text


def ask_question_with_sources(question: str):
    contexts = retrieve_context(question)

    context_text = build_context(contexts)

    prompt = (
        qa_prompt
        .replace("{context}", context_text)
        .replace("{question}", question)
    )

    response = generate_content(prompt)

    return response.text, contexts


def ask_question(question: str):
    answer, _ = ask_question_with_sources(question)
    return answer