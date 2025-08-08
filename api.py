from fastapi import FastAPI, HTTPException,status
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver 
from fastapi.responses import StreamingResponse
from asyncgraph import abot
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import logging, os
from dotenv import load_dotenv
import uuid
import asyncio
from typing import Annotated

from fastapi import Depends
from datetime import timedelta
from sqlalchemy.orm import Session
# Import authentication and user management functions from the auth module
from auth import (
    Token,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_user,
    UserCreate,
    get_db
)
from fastapi.security import OAuth2PasswordRequestForm

app = FastAPI()

# Make sure logs directory exists
os.makedirs("logs", exist_ok=True)

# Logger setup
logging.basicConfig(
    filename="logs/api.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


load_dotenv()
conn = os.getenv("DATABASE_URL")

memory = None

class QueryRequest(BaseModel):
    query: str
    session_id : str = None

import contextlib
memory = None
exit_stack = None

@app.on_event("startup")
async def startup_event():
    global memory, exit_stack
    try:
        # Initialize connection to async Postgres memory
        cm =AsyncPostgresSaver.from_conn_string(conn)
        # Keep connection open for the application lifetime, fix the 'connection is closed' Error
        exit_stack = contextlib.AsyncExitStack()
        memory = await exit_stack.enter_async_context(cm)  # async context manager
        await memory.setup()
        # Compile the agent with the memory
        abot.compile(memory)
        logging.info("Async Postgres memory initialized and agent compiled successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Async Postgres memory: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    global exit_stack
    # Properly close the async Postgres connection on shutdown
    if exit_stack:
        await exit_stack.aclose()
        logging.info("Async memory connection closed.")

def get_session_id(session_id: str = None):
    # Generate a new session ID if not provided
    return session_id or str(uuid.uuid4())


# Endpoint to register a new user in the database
@app.post("/signup")
async def signup(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """
    Create a new user account in the PostgreSQL database.
    """
    try:
        # Save new user to the database and return the username
        created_username = create_user(db, user)
        logging.info(f"User created: {created_username}")
        return {"message": f"User {created_username} created successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
        
# Login endpoint: returns JWT access token if credentials are valid 
@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    
    # Raise error if authentication fails
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set token expiration time
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Generate a JWT access token containing the username
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


# Requires a valid JWT token to access this endpoint
# The authenticated user is extracted via dependency injection
@app.post("/chat")
async def chat_endpoint(req: QueryRequest, current_user=Depends(get_current_active_user)):
    """
    Standard (non-streaming) chat endpoint.
    """
    try:
        # Use provided session_id or generate a new one
        session_id = get_session_id(req.session_id)
        # Define the config including session info
        config = {"configurable": {"thread_id": session_id}}
        # Create message from user query
        messages = [HumanMessage(content=req.query)]
        # Invoke the agent (sync)
        result = await abot.graph.ainvoke({"messages": messages}, config)
        # Extract the response content
        response = result["messages"][-1].content
        logging.info(f"User {current_user.username} | Session {session_id} | Query: {req.query} | Response: {response[:50]}...")
        return {"response": response, "session id": session_id}
    except Exception as e:
        logging.error(f"Error during chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----- Streaming Chat Endpoint -----
# Requires a valid JWT token to access this endpoint
# The authenticated user is extracted via dependency injection
@app.post("/chat/stream")
async def chat_stream(req: QueryRequest, current_user=Depends(get_current_active_user)):
    """
    Streaming chat endpoint.
    Streams partial responses (chunks) from the model as they are generated.
    """
    session_id = get_session_id(req.session_id)
    config = {"configurable": {"thread_id": session_id}}
    messages = [HumanMessage(content=req.query)]

    async def event_generator():
        """Yields model output chunks for StreamingResponse."""
        
        try:
            # Stream LangGraph events asynchronously
            async for event in abot.graph.astream_events({"messages": messages}, config):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        # Yield each chunk of the response immediately
                        yield chunk
            yield "\n"  # End of stream
        except Exception as e:
            logging.error(f"Error during streaming chat: {e}",exc_info=True)  # exc_info=True ensures full traceback is logged
            yield f"\n[Error]: {e}\n"
            
            
    # StreamingResponse sends chunks to the client as they are yielded
    return StreamingResponse(event_generator(), media_type="text/plain")

@app.get("/")
def home(query: str = ""):
    # Basic welcome message or response to a query
    return {"question": query or "Welcome to the API!"}