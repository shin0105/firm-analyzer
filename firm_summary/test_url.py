import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

client = OpenAI(
    base_url="https://models.github.ai/inference",
    api_key=GITHUB_TOKEN,
)

try:
    response = client.chat.completions.create(
        model="gpt-4o", # Try without prefix first
        messages=[
            {"role": "user", "content": "Hello"}
        ]
    )
    print("Success with gpt-4o")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Failed with gpt-4o: {e}")

try:
    response = client.chat.completions.create(
        model="openai/gpt-4o", # Try with prefix
        messages=[
            {"role": "user", "content": "Hello"}
        ]
    )
    print("Success with openai/gpt-4o")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Failed with openai/gpt-4o: {e}")
