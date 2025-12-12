import streamlit as st
import uuid
import pandas as pd
import json
from src.agent import Agent
from src.utils.db import get_db_connection

st.set_page_config(page_title="EchoDB - Database Chat Agent", layout="wide")
st.title("EchoDB - Database Chat Agent")

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "follow_up_count" not in st.session_state:
    st.session_state.follow_up_count = 0

if "processing" not in st.session_state:
    st.session_state.processing = False

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # Session Locking: Disable inputs if agent is active
    is_connected = st.session_state.agent is not None
    
    provider = st.selectbox(
        "Model Provider", 
        ["OpenAI", "Gemini", "Anthropic"], 
        disabled=is_connected
    )

    PROVIDER_MODELS = {
        "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-5-mini"],
        "Gemini": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
        "Anthropic": ["claude-haiku-4.5", "claude-3-5-sonnet-20240620", "claude-3-haiku-20240307"]
    }
    
    model_name = st.selectbox(
        "Model Name",
        PROVIDER_MODELS.get(provider, []),
        disabled=is_connected
    )
    
    api_key_label = f"{provider} API Key"
    api_key = st.text_input(api_key_label, type="password", disabled=is_connected)
    
    db_uri = st.text_input("Database URI", value="sqlite:///test.db", disabled=is_connected)
    
    if not is_connected:
        if st.button("Connect"):
            if not api_key:
                st.error(f"Please provide an {provider} API Key.")
            elif not db_uri:
                st.error("Please provide a Database URI.")
            else:
                with st.spinner("Connecting..."):
                    engine, error = get_db_connection(db_uri)
                    if error:
                        st.error(f"Connection failed: {error}")
                    else:
                        try:
                            st.session_state.agent = Agent(provider=provider, api_key=api_key, engine=engine, model_name=model_name)
                            st.session_state.messages = [] # Clear chat on new connection
                            st.session_state.follow_up_count = 0
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to initialize agent: {e}")

    if is_connected:
        st.success("✅ Connected to database")
        st.info(f"Using {provider}")
        if st.button("Disconnect"):
            st.session_state.agent = None
            st.session_state.messages = []
            st.session_state.follow_up_count = 0
            st.rerun()

    st.divider()
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.follow_up_count = 0
        st.rerun()


if not st.session_state.agent:
    st.info("Please connect to a database to start chatting.")
else:
    # Display chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        elif msg["role"] == "assistant":
            st.chat_message("assistant").write(msg["content"])
        elif msg["role"] == "tool_log":
            # Display tool logs in an expander
            with st.status(f"Tool: {msg['tool_name']}", state="complete"):
                st.write("Input:")
                st.json(msg['tool_input'])
                st.write("Output:")
                if isinstance(msg['tool_output'], str) and msg['tool_output'].startswith("|"):
                     st.markdown(msg['tool_output']) # Markdown table
                else:
                    st.code(msg['tool_output'])

    # Chat Input
    # Disable input if processing or limit reached
    disable_input = st.session_state.processing or st.session_state.follow_up_count >= 10
    
    if prompt := st.chat_input("Ask a question about your database", disabled=disable_input):
        if st.session_state.follow_up_count >= 10:
            st.error("Chat limit reached (10 messages). Please clear the chat to continue.")
        else:
            st.session_state.processing = True
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            st.session_state.follow_up_count += 1
            st.rerun()

    # Handle processing state
    if st.session_state.processing and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Container for tool logs
            current_tool_status = None
            current_tool_input = None
            
            # Prepare history for agent (filter out tool logs)
            agent_history = []
            for m in st.session_state.messages:
                if m["role"] in ["user", "assistant", "tool_log"]:
                    agent_history.append(m)
            
            error_occurred = False
            try:
                # Run agent chat
                # Pass cached schema if available
                schema = st.session_state.get("db_schema", None)
                
                for event in st.session_state.agent.chat(agent_history, schema=schema):
                    if event["type"] == "content":
                        full_response += event["content"]
                        message_placeholder.markdown(full_response + "▌")
                    
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
                                if isinstance(output, str) and output.startswith("|"):
                                     st.markdown(output)
                                else:
                                    st.code(output)
                            current_tool_status.update(label=f"Tool: {event['tool_name']}", state="complete")
                            
                            # Save tool log to history
                            st.session_state.messages.append({
                                "role": "tool_log",
                                "tool_name": event['tool_name'],
                                "tool_input": current_tool_input,
                                "tool_output": output
                            })
                            
                            # Cache schema if this was a get_schema call
                            # Cache schema if this was a get_schema call
                            if event['tool_name'] == 'get_schema':
                                if isinstance(output, dict):
                                    st.session_state.db_schema = output
                                elif isinstance(output, str):
                                    try:
                                        # Try to parse JSON string to avoid double encoding later
                                        st.session_state.db_schema = json.loads(output)
                                    except json.JSONDecodeError:
                                        st.session_state.db_schema = output

                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            except Exception as e:
                error_occurred = True
                st.error(f"An error occurred: {e}")
            
            finally:
                st.session_state.processing = False
            
            if not error_occurred:
                st.rerun()
