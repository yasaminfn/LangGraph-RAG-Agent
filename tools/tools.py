from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
#from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_tavily import TavilySearch
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json #the format we want to retrieve
import pprint
from dotenv import load_dotenv
import os
from dotenv import load_dotenv
from tools.rag_tool import qa_chain

load_dotenv()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY=os.getenv("TAVILY_API_KEY")
COINCAP_API_KEY=os.getenv("COINCAP_API_KEY")


@tool
def get_price(slug: str) -> str:
      """Gets the current price of a given cryptocurrency based on a API
        Example input: bitcoin  , output: 118,205.23 USD
      """
      url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
      parameters = {
        'slug': slug,
        'convert':'USD'
      }
      headers = {
        'Accepts': 'application/json', #selects return format, we want json in response
        'X-CMC_PRO_API_KEY': COINCAP_API_KEY,
      } #header is for the things that dont change in differev=nt sessions

      session = Session()
      session.headers.update(headers) #adding the headers to the session

      try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        slug_id=list(data["data"].keys())[0]
        #pprint.pprint(data["data"]["1"]["quote"]["USD"]["price"])
        print(f"price: {data['data'][slug_id]['quote']['USD']['price']} USD")
        return f"price: {data['data'][slug_id]['quote']['USD']['price']} USD"
      except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
        
tavily_tool=TavilySearch(max_results=2)

@tool
def rag_qa(query: str) -> str:
  
    """
    Answer user questions based on indexed PDF about a network architecture called the Transformer, which is based on attention mechanisms and eliminates the need for recurrence and convolutions using RAG pipeline.
    Input: a user question (query)
    Output: answer string
    """
    response = qa_chain.invoke(query)
    print(response)
    return response["answer"] if "answer" in response else str(response)
  
TOOLs = [get_price,tavily_tool,rag_qa]