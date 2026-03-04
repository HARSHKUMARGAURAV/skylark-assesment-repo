import os
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import create_react_agent

# 1. API Keys
os.environ["GROQ_API_KEY"] = "enter your api key"


def get_response_Ai_agent(llm_id, query, allow_search, system_prompt, provider):
    # Select Model Provider dynamically
    if provider == "OpenAI":
        llm = ChatOpenAI(model=llm_id)
    else:
        llm = ChatGroq(model=llm_id)

    # Setup Tools
    tools = []
    if allow_search:
        search_tool = TavilySearchResults(max_results=2)
        tools.append(search_tool)

    # Create Agent (Using 'prompt' for latest LangGraph)
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt 
    )

    # Invoke Agent with message list
    state = {"messages": query} # Backend sends list of strings
    response = agent.invoke(state)

    # Return only the last message content
    return response["messages"][-1].content