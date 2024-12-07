import os
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import pymupdf4llm

load_dotenv()

client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")

def split_text_into_chunks(text, max_tokens=1024):
    chunks = []
    words = text.split()
    for i in range(0, len(words), max_tokens):
        chunk = " ".join(words[i:i+max_tokens])
        chunks.append(chunk)
    return chunks

pdf_paths = ['./src/utils/knowledge_base/one.pdf', './src/utils/knowledge_base/two.pdf', './src/utils/knowledge_base/three.pdf', 
             './src/utils/knowledge_base/four.pdf', './src/utils/knowledge_base/five.pdf', './src/utils/knowledge_base/six.pdf',
             './src/utils/knowledge_base/seven.pdf', './src/utils/knowledge_base/eight.pdf', './src/utils/knowledge_base/nine.pdf',
             './src/utils/knowledge_base/ten.pdf', './src/utils/knowledge_base/eleven.pdf'
             ]

for pdf_path in pdf_paths:
    extracted_text = pymupdf4llm.to_markdown(pdf_path)
    chunks = split_text_into_chunks(extracted_text)

def get_embedding(text, model="text-embedding-3-small"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

chunk_embeddings = [{"text": chunk, "embedding": get_embedding(chunk)} for chunk in chunks]

vectordb_client = QdrantClient(
    url=os.getenv("QDRANT_URL"), 
    api_key=os.getenv("QDRANT_API_KEY")
)

# Uncomment to update knowledge base
vectordb_client.recreate_collection(
    collection_name="respiratory_disease_guide",
    vectors_config={"size": 1536, "distance": "Cosine"}
)

for idx, chunk in enumerate(chunk_embeddings):
    vectordb_client.upsert(
        collection_name="respiratory_disease_guide",
        points=[{
            "id": idx,  # Use the integer directly
            "vector": chunk["embedding"],
            "payload": {"text": chunk["text"]}
        }]
    )

# retrieval
def query_qdrant(query_text):
    query_embedding = get_embedding(query_text)
    search_result = vectordb_client.search(
        collection_name="respiratory_disease_guide",
        query_vector=query_embedding,
        limit=5
    )
    return [hit.payload["text"] for hit in search_result]

def rag_system(user_query):
    retrieved_contexts = query_qdrant(user_query)
    context_text = "\n".join(retrieved_contexts)
    
    messages = [
        {"role": "system", "content": "You are an AI doctor specializing in respiratory diseases. Respond to the user in a professional and conversational way. Provide clear, empathetic, and helpful guidance. Not too structured."},
        {"role": "system", "content": f"Retrieved Context: {context_text}"},
        {"role": "user", "content": user_query}
    ]
    
    # Generate the response using ChatCompletion endpoint
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=200,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()

user_query = "I have a fever"
response = rag_system(user_query)
print(response)

### CHECKER
# def check_number_of_points(vectordb_client, collection_name):
#     count = vectordb_client.count(collection_name=collection_name).count
#     return count

# collection_name = "respiratory_disease_guide"
# number_of_points = check_number_of_points(vectordb_client, collection_name)
# print(f"The collection '{collection_name}' contains {number_of_points} points.")