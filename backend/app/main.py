import os
import sys
import logging
from datetime import datetime
from typing import Annotated
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add the app directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from services.llm_service import LLMService

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

# Initialize LLM service
llm_service = LLMService()

@app.post("/api/chat")
async def chat_endpoint(message: Annotated[ChatMessage, "Chat message"]):
    try:
        # Log incoming request
        logger.info(f" Received new query: {message.message}")

        # Track timing
        start_time = datetime.now()

        # Check if it's input for a pending INSERT query
        is_insert_input = llm_service.is_insert_value_input(message.message)
        if is_insert_input:
            logger.info(f" Query type: INSERT field input")
            response_data = llm_service.process_insert_value_input(message.message)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f" INSERT field input processed in {processing_time:.2f} seconds")

            return response_data

        # Check if it's a follow-up question
        is_follow_up = llm_service.is_follow_up_question(message.message)
        logger.info(f"{'🔄' if is_follow_up else '🆕'} Query type: {'Follow-up' if is_follow_up else 'New query'}")

        # Generate response using LLM (now returns JSON)
        response_data = llm_service.generate_response(message.message)

        # Log completion
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f" Query processed in {processing_time:.2f} seconds")

        # Return the JSON response directly
        return response_data
    except Exception as e:
        logger.error(f"❌ Error processing query: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "sql_query": "",
            "explanation": "",
            "data": None
        }
