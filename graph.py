 
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain.tools import tool
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json #the format we want to retrieve
import pprint
from tools.tools import TOOLs

import logging  # Import Python's built-in logging module
import os       # Import os module to work with the file system

os.makedirs("logs", exist_ok=True)  # Create a "logs" directory if it doesn't exist

logger = logging.getLogger("file_api_logger")  # Create a custom logger named "file_api_logger"
logger.setLevel(logging.INFO)  # Set logging level to INFO

file_handler = logging.FileHandler("logs/app.log")  # Log messages will be written to logs/app.log

formatter = logging.Formatter(  # Define the format of log messages
    "%(asctime)s, %(api_path)s, %(levelname)s, %(message)s",
    datefmt="%Y-%m-%d, %H:%M:%S"
)

file_handler.setFormatter(formatter)  # Attach the formatter to the file handler
logger.addHandler(file_handler)  # Add the file handler to the logger

from langgraph.checkpoint.memory import MemorySaver
#memory
memory = MemorySaver()

import uuid
#thread id for each session
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

model = ChatOpenAI(model="gpt-4o-mini")
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    
class Agent:


    #tools = [Agent.get_price,TavilySearch(max_results=2)]

    def __init__(self, model, tools, system=""):
        self.system = system
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_openai)
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges(
            "llm",
            self.exists_action,
            {True: "action", False: END}
        )
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile(checkpointer=memory)
        self.tools = {getattr(t, "__name__", getattr(t, "name", str(t))): t for t in tools}
        self.model = model.bind_tools(tools)

    def exists_action(self, state: AgentState):
        result = state['messages'][-1]
        return len(result.tool_calls) > 0

    def call_openai(self, state: AgentState):
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return {'messages': [message]}

    def take_action(self, state: AgentState):
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            print(f"Calling: {t}")
            print(f"Arguments: {t['args']}")
            if not t['name'] in self.tools:      # check for bad tool name from LLM
                print("\n ....bad tool name....")
                result = "bad tool name, retry"  # instruct LLM to retry if bad
            else:
                result = self.tools[t['name']].invoke(t['args'])
                print(result)
            results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))
        print("Back to the model!")
        return {'messages': results}

abot = Agent(
    model=model,
    tools=TOOLs,
    system="You are a helpful assistant",
)



while(True):
    #question
    query = input("**Please enter your question: ")

    if query.lower() == 'exit':
        logger.info("User exited the chat", extra={"api_path": "user_query"})
        break
    
    logger.info("User entered a question", extra={"api_path": "user_query"})
    logger.info(f"User query: {query}", extra={"api_path": "user_query"})
    
    try:
        messages = [HumanMessage(content=query)]
        result = abot.graph.invoke({"messages": messages}, config)
        print(result['messages'][-1].content)
        
    except Exception as e:
        logger.error(f"Error during chat: {e}", extra={"api_path": "llm_response"})
        
