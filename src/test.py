import os
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")
print(client.api_key)
response = client.chat.completions.create(
    model="gpt-4o-mini",  # Use the desired GPT model (e.g., gpt-3.5-turbo, gpt-4)
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a haiku about recursion in programming."},
    ],  # Provide the conversation history
    temperature=0.7,  # Controls creativity
    max_tokens=500,  # Limits the length of the response
)

print(response.choices[0].message.content)
