# DEVELOPMENT/TEST ONLY — not used in production
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=200,
)

messages = [
    SystemMessage(content="You are a helpful Singapore P1 school registration advisor."),
    HumanMessage(content="What is Phase 2C in Singapore primary school registration?"),
]

response = llm.invoke(messages)
print(response.content)