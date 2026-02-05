import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

class SimpleMemory:
    def __init__(self):
        self.chat_history = []

    def load_memory_variables(self, _):
        # Format history as (role, content) logic if needed, 
        # but for ChatGoogleGenerativeAI we usually pass a list of messages.
        return {"chat_history": self.chat_history}

    def save_context(self, inputs, outputs):
        # inputs is usually {"question": ...}, outputs is {"output": ...}
        input_text = inputs.get("question") or inputs.get("input")
        output_text = outputs.get("output") or outputs.get("text")
        
        if input_text:
            from langchain_core.messages import HumanMessage
            self.chat_history.append(HumanMessage(content=input_text))
        if output_text:
            from langchain_core.messages import AIMessage
            self.chat_history.append(AIMessage(content=output_text))

class AIRecommender:
    def __init__(self):
        # Try finding API Key or load from safe location
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            # We don't raise error immediately to allow UI to handle it gracefully if key is missing
            print("Warning: GOOGLE_API_KEY not set.")
        
        # If imports fail here, it's likely a packaging issue, but these are essential
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            convert_system_message_to_human=True,
            google_api_key=api_key
        )
        
        # Use our simple memory to avoid 'langchain.memory' import issues
        self.memory = SimpleMemory()

    def classify_games(self, game_names: List[str]):
        """
        Uses Gemini to classify a list of games by genre and style.
        """
        parser = JsonOutputParser(pydantic_object=GameList)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Steam game expert. Classify the following games into Genre, Play Style, and Vibe. Return strict JSON."),
            ("human", "Classify these games:\n{game_names}\n\n{format_instructions}")
        ])

        chain = prompt | self.llm | parser

        try:
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
        
        # Load history
        history = self.memory.load_memory_variables({})["chat_history"]
        
        response = chain.invoke({
            "library_context": library_context,
            "chat_history": history,
            "question": user_query
        })
        
        # Save context
        self.memory.save_context({"question": user_query}, {"output": response.content})
        
        return response.content
