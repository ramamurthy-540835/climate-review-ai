import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = "ai-ippc"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

model = GenerativeModel("gemini-2.5-flash")

response = model.generate_content("Hello Gemini!")

print(response.text)