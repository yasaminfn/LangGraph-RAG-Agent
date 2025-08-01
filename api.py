from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.postgres import PostgresSaver
from graph import abot
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import logging, os
from dotenv import load_dotenv
import uuid

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

@app.on_event("startup")
def startup_event():
    global memory, exit_stack
    try:
        # Initialize connection to Postgres memory
        cm = PostgresSaver.from_conn_string(conn)
        # Keep connection open for the application lifetime, fix the "cinnection is closed" Error
        exit_stack = contextlib.ExitStack()
        memory = exit_stack.enter_context(cm)  # keep connection open
        memory.setup()
        # Compile the agent with the memory
        abot.compile(memory)
        logging.info("Postgres memory initialized and agent compiled successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Postgres memory: {e}")
        raise

@app.on_event("shutdown")
def shutdown_event():
    global exit_stack
    # Properly close the Postgres connection on shutdown
    exit_stack.close()
    logging.info("Memory connection closed.")

def get_session_id(session_id: str = None):
    # Generate a new session ID if not provided
    return session_id or str(uuid.uuid4())


@app.post("/chat")
def chat_endpoint(req: QueryRequest):
        try:
            # Use provided session_id or generate a new one
            session_id = get_session_id(req.session_id)
            # Define the config including session info
            config = {"configurable": {"thread_id": session_id}}
            # Create message from user query
            messages = [HumanMessage(content=req.query)]
            # Invoke the agent
            result = abot.graph.invoke({"messages": messages}, config)
            # Extract the response content
            response = result["messages"][-1].content
            logging.info(f"Session {session_id} | Query: {req.query} | Response: {response[:50]}...")
            return {"response": response, "session id": session_id}
        except Exception as e:
            logging.error(f"Error during chat request: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        
@app.get("/")
def home(query: str = ""):
    # Basic welcome message or response to a query
    return {"question": query or "Welcome to the API!"}