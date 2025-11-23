import streamlit as st
import uuid
import json
from src.agent import Agent
from src.utils.db import get_db_connection
from src.config import PROVIDER_MODELS, MAX_MESSAGES
from src.types import ChatMessage, ToolLog

st.set_page_config(page_title="EchoDB - Database Chat Agent", layout="wide")
st.title("EchoDB - Database Chat Agent")


# Helper functions
def clear_session_state() -> None:
    """Clear chat-related session state."""
    st.session_state.messages = []
    if "db_schema" in st.session_state:
        del st.session_state.db_schema


def render_tool_output(output: str) -> None:
    """Render tool output, detecting markdown tables.
    
    Args:
        output: Tool output string to render
    """
    if isinstance(output, str) and output.startswith("|"):
        st.markdown(output)  # Markdown table
    else:
        st.code(output)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "processing" not in st.session_state:
    st.session_state.processing = False

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # Session Locking: Disable inputs if agent is active
    is_connected = st.session_state.agent is not None
    
    provider = st.selectbox(
        "Model Provider", 
        ["OpenAI", "Google", "Anthropic", "X-AI"], 
        disabled=is_connected
    )

    model_name = st.selectbox(
        "Model Name",
        PROVIDER_MODELS.get(provider, []),
        disabled=is_connected
    )

    db_uri = st.text_input("Database URI", value="sqlite:///test.db", disabled=is_connected)
    
    if not is_connected:
        if st.button("Connect"):
            if not db_uri:
                st.error("Please provide a Database URI.")
            else:
                with st.spinner("Connecting..."):
                    engine, error = get_db_connection(db_uri)
                    if error:
                        st.error(f"Connection failed: {error}")
                    else:
                        try:
                            st.session_state.agent = Agent(provider=provider, engine=engine, model_name=provider.lower() + "/" + model_name)
                            clear_session_state()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to initialize agent: {e}")

    if is_connected:
        st.success("✅ Connected to DB!")
        if st.button("Disconnect"):
            st.session_state.agent = None
            clear_session_state()
            st.rerun()

    st.divider()
    if st.button("Clear Chat"):
        clear_session_state()
        st.rerun()


if not st.session_state.agent:
    st.info("Please connect to a database to start chatting.")
else:
    # Display chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                # Display tool logs associated with this message
                st.write(msg["content"])
                if "tool_logs" in msg and msg["tool_logs"]:
                    for tool_log in msg["tool_logs"]:
                        with st.status(f"Tool: {tool_log['tool_name']}", state="complete"):
                            st.write("Input:")
                            st.json(tool_log['tool_input'])
                            st.write("Output:")
                            render_tool_output(tool_log['tool_output'])

    # Chat Input
    # Disable input if processing or limit reached
    message_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    disable_input = st.session_state.processing or message_count >= MAX_MESSAGES
    
    if prompt := st.chat_input("Ask a question about your database", disabled=disable_input):
        if message_count >= MAX_MESSAGES:
            st.error(f"Chat limit reached ({MAX_MESSAGES} messages). Please clear the chat to continue.")
        else:
            st.session_state.processing = True
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            st.rerun()

    # Handle processing state
    if st.session_state.processing and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Container for tool logs for this message
            current_tool_status = None
            current_tool_input = None
            message_tool_logs = []  # Store tool logs for this specific message
            
            error_occurred = False
            try:
                # Get the last user message
                user_message = st.session_state.messages[-1]["content"]
                
                # Pass cached schema if available
                schema = st.session_state.get("db_schema", None)
                
                # Loading indicator
                spinner_placeholder = st.empty()
                spinner_placeholder.markdown("Thinking...")
                
                first_event_received = False

                for event in st.session_state.agent.chat(user_message, st.session_state.session_id, schema=schema):
                    if not first_event_received:
                        spinner_placeholder.empty()
                        first_event_received = True

                    if event["type"] == "content":
                        full_response += event["content"]
                        message_placeholder.markdown(full_response + " ▌")
                    
                    elif event["type"] == "tool_start":
                        current_tool_input = event['tool_input']
                        current_tool_status = st.status(f"Executing {event['tool_name']}...", expanded=True)
                        with current_tool_status:
                            st.write("Input:")
                            st.json(event['tool_input'])
                            
                    elif event["type"] == "tool_end":
                        if current_tool_status:
                            with current_tool_status:
                                st.write("Output:")
                                output = event['tool_output']
                                render_tool_output(output)
                            current_tool_status.update(label=f"Tool: {event['tool_name']}", state="complete")
                            
                            # Save tool log for this message
                            message_tool_logs.append({
                                "tool_name": event['tool_name'],
                                "tool_input": current_tool_input,
                                "tool_output": output
                            })
                            
                            # Cache schema if this was a get_schema call
                            if event['tool_name'] == 'get_schema':
                                if isinstance(output, dict):
                                    st.session_state.db_schema = output
                                elif isinstance(output, str):
                                    try:
                                        st.session_state.db_schema = json.loads(output)
                                    except json.JSONDecodeError:
                                        st.session_state.db_schema = output

                message_placeholder.markdown(full_response)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response,
                    "tool_logs": message_tool_logs  # Attach tool logs to this message
                })
            
            except Exception as e:
                error_occurred = True
                st.error(f"An error occurred: {e}")
            
            finally:
                st.session_state.processing = False
            
            if not error_occurred:
                st.rerun()
