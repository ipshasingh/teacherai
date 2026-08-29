from llm.client import LLMClient
from agents.extractor import extract_knowledge

client = LLMClient()
result = extract_knowledge(
    client,
    topic="Photosynthesis",
    known_concepts=[],
    user_text="Photosynthesis converts light energy into chemical energy. Plants use chlorophyll to absorb sunlight.",
)
print(result.model_dump_json(indent=2))
client.close()