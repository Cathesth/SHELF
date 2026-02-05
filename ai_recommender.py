import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List

load_dotenv()

# Map GEMINI_API_KEY to GOOGLE_API_KEY if needed, or just use it directly
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

class GameClassification(BaseModel):
    game_name: str = Field(description="Name of the game")
    genre: str = Field(description="Main genre of the game (e.g., RPG, FPS, Strategy, Puzzle)")
    play_style: str = Field(description="Play style (e.g., Single-player, Multiplayer, Co-op)")
    vibe: str = Field(description="Vibe or difficulty (e.g., Casual, Hardcore, Story-rich)")

class GameList(BaseModel):
    games: List[GameClassification]

class AIRecommender:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) not found.")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            convert_system_message_to_human=True
        )
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    def classify_games(self, game_names: List[str]):
        """
        Uses Gemini to classify a list of games by genre and style.
        """
        # Batching could be done here if list is too large, 
        # but Gemini 1.5 Flash has a large context window, so we'll try sending all (up to a limit).
        # We limit to top 50-100 in the UI to avoid timeouts if list is huge.
        
        parser = JsonOutputParser(pydantic_object=GameList)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Steam game expert. Classify the following games into Genre, Play Style, and Vibe. Return strict JSON."),
            ("human", "Classify these games:\n{game_names}\n\n{format_instructions}")
        ])

        chain = prompt | self.llm | parser

        try:
            # Join names for prompt
            games_str = ", ".join(game_names)
            result = chain.invoke({
                "game_names": games_str,
                "format_instructions": parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"Error classifying games: {e}")
            return {"games": []}

    def get_recommendation(self, user_query: str, library_context: str):
        """
        Generates a recommendation based on user query and library context.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful Steam library assistant. You have access to the user's game library stats and classifications."),
            ("system", "Context about user's library: {library_context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

        chain = prompt | self.llm
        
        # We handle memory manually for the simple chain invocation
        history = self.memory.load_memory_variables({})["chat_history"]
        
        response = chain.invoke({
            "library_context": library_context,
            "chat_history": history,
            "question": user_query
        })
        
        # Save context
        self.memory.save_context({"question": user_query}, {"output": response.content})
        
        return response.content
