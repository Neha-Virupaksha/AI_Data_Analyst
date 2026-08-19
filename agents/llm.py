from langchain_ollama import ChatOllama

# One model for every agent, per the spec's reasoning: avoids Ollama's
# reload overhead when the graph hands off between agents on 8GB RAM.
llm = ChatOllama(model="qwen2.5-coder:7b", temperature=0.1)
