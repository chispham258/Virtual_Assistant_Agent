import json
import uuid

import requests
import streamlit as st

API_URL = "http://localhost:8080"

st.set_page_config(
    page_title="Virtual Assistant",
    page_icon="🤖",
    layout="centered",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Virtual Assistant")
    st.caption("Powered by Notion · Gmail · Google Calendar")

    st.divider()

    if st.button("New conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    st.caption(f"Thread: `{st.session_state.get('thread_id', '')[:8]}…`")

    st.divider()
    st.markdown(
        "**Available agents**\n"
        "- 📝 **Notion** — pages & databases\n"
        "- 📧 **Gmail** — email\n"
        "- 📅 **Calendar** — events & scheduling"
    )

# ── Session state init ─────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render conversation history ────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask me anything…"):

    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response
    with st.chat_message("assistant"):
        def _stream():
            try:
                with requests.post(
                    f"{API_URL}/chat_stream",
                    json={"query": prompt, "thread_id": st.session_state.thread_id},
                    stream=True,
                    timeout=120,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line)
                            if data.get("content"):
                                yield data["content"]
            except requests.exceptions.ConnectionError:
                yield "⚠️ Could not connect to the backend. Make sure the server is running on port 8080."
            except requests.exceptions.HTTPError as e:
                yield f"⚠️ Server error: {e}"
            except Exception as e:
                yield f"⚠️ Unexpected error: {e}"

        reply = st.write_stream(_stream())

    st.session_state.messages.append({"role": "assistant", "content": reply})
