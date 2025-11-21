import json
import uuid
from typing import Literal, Annotated, Sequence, TypedDict, Union, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from src.tools.get_schema import get_get_schema_tool
from src.tools.execute_query import get_execute_query_tool
from src.tools.get_table_sample import get_get_table_sample_tool
from src.prompts.system import get_system_prompt

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

class Agent:
    def __init__(self, provider: str, api_key: str, engine, model_name: str = None):
        self.engine = engine
        self.provider = provider
        
        # Get tools
        self.tools = [
            get_get_schema_tool(engine),
            get_execute_query_tool(engine),
            get_get_table_sample_tool(engine)
        ]

        # Initialize LLM based on provider
        if provider == "OpenAI":
            self.llm = ChatOpenAI(
                api_key=api_key, 
                model=model_name or "gpt-4o",
                temperature=0,
                max_retries=5
            )
        elif provider == "Gemini":
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=api_key, 
                model=model_name or "gemini-2.5-flash-lite",
                temperature=0,
                max_retries=5
            )
        elif provider == "Anthropic":
            self.llm = ChatAnthropic(
                api_key=api_key, 
                model=model_name or "claude-3-haiku-20240307",
                temperature=0,
                max_retries=5
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Build Graph
        workflow = StateGraph(AgentState)

        def call_model(state):
            messages = state['messages']
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(self.tools))

        workflow.add_edge(START, "agent")
        
        def should_continue(state):
            messages = state['messages']
            last_message = messages[-1]
            if last_message.tool_calls:
                return "tools"
            return END

        workflow.add_conditional_edges("agent", should_continue, ["tools", END])
        workflow.add_edge("tools", "agent")

        self.app = workflow.compile()

    def chat(self, messages, schema=None):
        """
        Processes the chat conversation.
        Input messages: list of dicts {"role": "...", "content": "..."}
        Yields events:
        - {"type": "content", "content": "..."}
        - {"type": "tool_start", "tool_name": "...", "tool_input": {...}}
        - {"type": "tool_end", "tool_name": "...", "tool_output": ...}
        """
        
        # System prompt
        system_content = get_system_prompt(schema)
            
        # Reconstruct LangChain messages
        lc_messages = [SystemMessage(content=system_content)]
        
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "tool_log":
                # Retroactively attach tool call to the last AIMessage
                # If the last message is not an AIMessage (e.g. it's a HumanMessage),
                # we need to insert a dummy AIMessage to hold the tool call.
                if not lc_messages or not isinstance(lc_messages[-1], AIMessage):
                    lc_messages.append(AIMessage(content=""))

                if isinstance(lc_messages[-1], AIMessage):
                    # Use UUID for robust ID generation
                    tool_call_id = str(uuid.uuid4())
                    if not lc_messages[-1].tool_calls:
                        lc_messages[-1].tool_calls = []
                    
                    lc_messages[-1].tool_calls.append({
                        "name": msg["tool_name"],
                        "args": msg["tool_input"],
                        "id": tool_call_id
                    })
                    
                    lc_messages.append(ToolMessage(
                        tool_call_id=tool_call_id,
                        content=str(msg["tool_output"]),
                        name=msg["tool_name"]
                    ))

        input_state = {"messages": lc_messages}
        
        # Stream events
        for step in self.app.stream(input_state, stream_mode="updates"):
            if "agent" in step:
                # Agent finished a step
                message = step["agent"]["messages"][0]
                if message.content:
                    content = message.content
                    if isinstance(content, list):
                        final_content = ""
                        for part in content:
                            if isinstance(part, dict) and "text" in part:
                                final_content += part["text"]
                            elif isinstance(part, str):
                                final_content += part
                            else:
                                final_content += str(part)
                        content = final_content
                    yield {"type": "content", "content": content}
                
                if message.tool_calls:
                    for tc in message.tool_calls:
                        yield {"type": "tool_start", "tool_name": tc["name"], "tool_input": tc["args"]}
            
            if "tools" in step:
                # Tools finished a step
                tool_messages = step["tools"]["messages"]
                for tm in tool_messages:
                    yield {"type": "tool_end", "tool_name": tm.name, "tool_output": tm.content}
