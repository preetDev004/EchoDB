import json
from typing import Literal, Annotated, List, Iterator, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLM
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from src.tools.get_schema import create_schema_tool
from src.tools.execute_query import create_query_tool
from src.tools.get_table_sample import create_sample_tool
from src.prompts.system import get_system_prompt
from src.types import AgentEvent
from dotenv import load_dotenv
import os

load_dotenv()

class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[List[BaseMessage], add_messages]

class Agent:
    """Database chat agent using LangGraph with persistent state."""
    
    def __init__(self, provider: str, engine, model_name: str = None):
        """Initialize the agent with database connection and LLM.
        
        Args:
            provider: Model provider name (OpenAI, Gemini, Anthropic)
            engine: SQLAlchemy engine instance
            model_name: Full model name including provider prefix
        """
        self.engine = engine
        self.provider = provider
        
        # Get tools
        self.tools = [
            create_schema_tool(engine),
            create_query_tool(engine),
            create_sample_tool(engine)
        ]

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

        # Initialize LLM based on provider
        self.llm = ChatLiteLLM(
            openrouter_api_key=api_key, 
            api_base="https://openrouter.ai/api/v1",
            model="openrouter/" + model_name,
            temperature=0,
            max_retries=5,
            streaming=True
        )

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Build Graph with checkpointing
        workflow = StateGraph(AgentState)

        def call_model(state: AgentState) -> dict:
            """Agent node that calls the LLM."""
            messages = state['messages']
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}

        def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
            """Determine whether to continue to tools or end."""
            messages = state['messages']
            last_message = messages[-1]
            if last_message.tool_calls:
                return "tools"
            return END
        
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue, ["tools", END])
        workflow.add_edge("tools", "agent")

        # Compile with memory checkpointer for state persistence
        self.checkpointer = MemorySaver()
        self.app = workflow.compile(checkpointer=self.checkpointer)

    def chat(self, user_message: str, thread_id: str, schema: dict = None) -> Iterator[AgentEvent]:
        """Process a chat message and yield events.
        
        Args:
            user_message: The user's message
            thread_id: Unique thread ID for conversation persistence
            schema: Optional cached database schema to include in system prompt
            
        Yields:
            AgentEvent dictionaries with type, content, and other relevant fields
        """
        # Get current state to check if this is the first message
        config = {"configurable": {"thread_id": thread_id}}
        current_state = self.app.get_state(config)
        
        # Build input - add system message only on first message
        if not current_state.values or len(current_state.values.get("messages", [])) == 0:
            # First message in thread - include system prompt
            system_content = get_system_prompt(schema)
            input_messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_message)
            ]
        else:
            # Continuing conversation - just add user message
            input_messages = [HumanMessage(content=user_message)]
        
        input_state = {"messages": input_messages}
        
        # Stream events from the graph
        for mode, payload in self.app.stream(input_state, config, stream_mode=["messages", "updates"]):
            if mode == "messages":
                msg, metadata = payload
                # Only stream content from the agent node
                if metadata.get("langgraph_node") == "agent":
                    if msg.content:
                        yield {"type": "content", "content": msg.content}
            
            elif mode == "updates":
                step = payload
                if "agent" in step:
                    # Agent finished a step, check for tool calls
                    message = step["agent"]["messages"][0]
                    if message.tool_calls:
                        for tc in message.tool_calls:
                            yield {"type": "tool_start", "tool_name": tc["name"], "tool_input": tc["args"]}
                
                if "tools" in step:
                    # Tools finished a step
                    tool_messages = step["tools"]["messages"]
                    for tm in tool_messages:
                        yield {"type": "tool_end", "tool_name": tm.name, "tool_output": tm.content}
