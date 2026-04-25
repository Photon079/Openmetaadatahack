import os
import sys

# Add the root directory to sys.path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GEMINI_API_KEY

class GeminiAgent:
    def __init__(self, model_name: str = "gemini-2.5-flash"): # Recommended over flash-lite for reasoning
        # Initializing the core LLM. Provide API key via env var GEMINI_API_KEY
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            convert_system_message_to_human=True,
            google_api_key=GEMINI_API_KEY
        )

    def process(self, system_prompt: str, user_input: Any, output_schema: type[BaseModel]):
        """Generic method to process node logic with structured output."""
        structured_llm = self.llm.with_structured_output(output_schema)
        response = structured_llm.invoke([
            ("system", system_prompt),
            ("human", str(user_input))
        ])
        return response
    

if __name__ == "__main__":
    from pydantic import Field
    import json
    
    # 1. Define a dummy schema for testing
    class TestClassification(BaseModel):
        sentiment: str = Field(description="The sentiment of the text (Positive, Negative, Neutral)")
        confidence: float = Field(description="Confidence score between 0.0 and 1.0")
        entities: list[str] = Field(description="List of key entities mentioned")

    print("Initializing GeminiAgent...")
    try:
        agent = GeminiAgent()
        
        test_prompt = "Analyze the text and extract sentiment, confidence, and entities."
        test_input = "OpenMetadata integration is running smoothly, but the legacy SQL server keeps dropping connections."
        
        print(f"\nTesting input: '{test_input}'")
        print("Calling LLM... (This requires GEMINI_API_KEY to be set)")
        
        # 2. Process the input
        result = agent.process(
            system_prompt=test_prompt, 
            user_input=test_input, 
            output_schema=TestClassification
        )
        
        # 3. Print the strongly typed result
        print("\n--- LLM Structured Output ---")
        print(result.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        print("Did you forget to run: export GEMINI_API_KEY='your_key_here' ?")