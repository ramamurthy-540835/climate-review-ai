from services.llm_service import ask_question

question = "How can cities reduce greenhouse gas emissions?"

answer = ask_question(question)

print("\n")
print("=" * 80)
print(answer)
print("=" * 80)