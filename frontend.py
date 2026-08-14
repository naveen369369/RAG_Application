"""
Enterprise Production RAG Studio — Light Theme Frontend
=========================================================
A state-of-the-art, production-grade light-themed web interface for the FastAPI RAG backend.

Features:
    💬 Real-Time Streaming Chat — Word-by-word streaming AI response generation
    ⚡ Starter Suggestion Chips — ChatGPT-style suggestion cards
    📂 Sidebar Document Studio  — Index files into Pinecone (Table + Section + Semantic)
    ➕ New Chat Control        — Instant conversation reset
"""

import time
import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = "http://localhost:8000"
SUPPORTED_TYPES = ["txt", "md", "pdf", "docx", "csv", "json", "html", "htm"]

st.set_page_config(
    page_title="Enterprise RAG Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS Design System: Exact ChatGPT Color Palette & Typography
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Söhne:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* ── Main Canvas (ChatGPT Pure White Canvas) ── */
    .stApp {
        background-color: #ffffff !important;
        color: #0d0d0d !important;
    }

    /* ── Center Chat Feed Container (Max-Width 800px) ── */
    .main .block-container {
        max-width: 800px !important;
        padding-top: 1.8rem !important;
        padding-bottom: 6rem !important;
    }

    /* ── Sidebar (Light Theme Color) ── */
    section[data-testid="stSidebar"] {
        background-color: #f9f9f9 !important;
        border-right: 1px solid #e5e5e5 !important;
        color: #0d0d0d !important;
    }
    section[data-testid="stSidebar"] * {
        color: #0d0d0d !important;
    }

    /* ── ChatGPT Signature Emerald Green Accent (#10a37f) ── */
    .chatgpt-green {
        color: #10a37f !important;
    }
    
    .chatgpt-badge {
        background: rgba(16, 163, 127, 0.12);
        color: #10a37f !important;
        border: 1px solid rgba(16, 163, 127, 0.25);
        padding: 3px 10px;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.78rem;
    }

    /* ── Buttons (Primary Emerald Green) ── */
    .stButton > button {
        background-color: #10a37f !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 0.6rem 1.4rem !important;
        transition: background-color 0.2s ease, transform 0.15s ease !important;
        box-shadow: 0 2px 6px rgba(16, 163, 127, 0.2) !important;
    }
    .stButton > button:hover {
        background-color: #0e8e6f !important;
        transform: translateY(-1px) !important;
    }

    /* ── Sidebar New Chat Button ── */
    div[data-testid="stSidebar"] .stButton > button {
        background-color: #ffffff !important;
        border: 1.5px solid #000000 !important;
        color: #0d0d0d !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f0f0f0 !important;
        border-color: #000000 !important;
    }

    /* ── ChatGPT Prompt Suggestion Cards ── */
    .suggestion-card {
        background: #ffffff;
        border: 1.5px solid #000000;
        border-radius: 16px;
        padding: 16px;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .suggestion-card:hover {
        border-color: #10a37f;
        background: #f9f9f9;
        transform: translateY(-2px);
    }

    /* ── Source Attribution Card ── */
    .source-box {
        background: #f9f9f9;
        border: 1.5px solid #000000;
        border-left: 5px solid #10a37f;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 8px;
        font-size: 0.88rem;
        color: #353740;
    }

    /* ── Text Boxes & Input Controls (Single Clean Black Border, No Double Borders) ── */
    .stTextArea > div,
    .stTextInput > div,
    .stSelectbox > div,
    [data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border:2.5px solid #000000 !important;
        border-radius: 12px !important;
    }

    /* Remove inner nested borders inside textboxes */
    .stTextArea textarea,
    .stTextInput input,
    .stSelectbox select,
    .stSelectbox [data-baseweb="select"],
    [data-testid="stChatInput"] textarea {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
        color: #0d0d0d !important;
    }

    .stTextArea > div:focus-within,
    .stTextInput > div:focus-within,
    .stSelectbox > div:focus-within,
    [data-testid="stChatInput"]:focus-within {
        border-color: #000000 !important;
        box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.15) !important;
    }

    /* ── Scrollbars ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #ffffff; }
    ::-webkit-scrollbar-thumb { background: #d9d9e3; border-radius: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# API Helper Functions
# ---------------------------------------------------------------------------

def api_post(path: str, **kwargs):
    """POST request helper to FastAPI backend."""
    try:
        r = httpx.post(f"{API_BASE}{path}", timeout=300, **kwargs)
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, "Cannot connect to backend. Verify `uvicorn main:app --port 8000` is running."
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = exc.response.text or str(exc)
        return None, f"API Error ({exc.response.status_code}): {detail}"
    except Exception as exc:
        return None, str(exc)


def api_get(path: str, params: dict = None):
    """GET request helper to FastAPI backend."""
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, timeout=60)
        r.raise_for_status()
        return r.json(), None
    except Exception as exc:
        return None, str(exc)

# ---------------------------------------------------------------------------
# Sidebar (ChatGPT Dark Charcoal #171717)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 15px 0 10px 0; display:flex; align-items:center; gap:10px;">
            <div style="font-size:1.8rem;">⚡</div>
            <div>
                <div style="font-size:1.25rem; font-weight:700; color:#0d0d0d !important;">Enterprise Production RAG </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ➕ New Chat Button
    if st.button("➕ New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("<hr style='border-color:#2f2f2f; margin:15px 0;'>", unsafe_allow_html=True)

    # Search Target Namespace Selector
    ns_resp, _ = api_get("/namespaces")
    active_namespaces = ns_resp.get("namespaces", ["default"]) if ns_resp else ["default"]

    ns_options = ["🌐 All Namespaces (Auto-Search)"] + active_namespaces + ["✏️ Custom Namespace..."]
    ns_selection = st.selectbox(
        "Vector Search Space",
        options=ns_options,
        key="ns_search_select",
        help="Select 'All Namespaces' to query across all uploaded documents automatically.",
    )
    if ns_selection == "🌐 All Namespaces (Auto-Search)":
        selected_namespace = "all"
    elif ns_selection == "✏️ Custom Namespace...":
        selected_namespace = st.text_input("Enter namespace name:", value="default", key="custom_search_ns")
    else:
        selected_namespace = ns_selection

    show_sources = st.checkbox("Show Sources Attribution", value=True)
    use_reranker = st.toggle(
        "⚡ Cross-Encoder Reranking",
        value=False,
        key="use_reranker",
        help="Retrieve 2× more candidates, then rerank with a cross-encoder before answering. More accurate, slightly slower.",
    )

    st.markdown("<hr style='border-color:#2f2f2f; margin:15px 0;'>", unsafe_allow_html=True)

    # 📂 Document Indexing Studio Expander
    with st.expander("📂 Document Indexing Studio", expanded=False):
        uploaded_files = st.file_uploader(
            "Upload Files",
            type=SUPPORTED_TYPES,
            accept_multiple_files=True,
            help="PDF, TXT, Markdown, Word, CSV, JSON, HTML",
        )

        if uploaded_files:
            strategy_choice = st.selectbox(
                "Chunking Strategy",
                options=["Hybrid (Table + Section + Semantic)", "Fixed + Overlap"],
                index=0,
            )

            ns_idx_options = ["✨ Auto-Generate from Filename"] + active_namespaces + ["✏️ Custom..."]
            ns_idx_sel = st.selectbox("Destination Namespace", options=ns_idx_options, key="ns_idx_select")

            if ns_idx_sel == "✨ Auto-Generate from Filename":
                index_namespace = "auto"
            elif ns_idx_sel == "✏️ Custom...":
                index_namespace = st.text_input("Custom Namespace:", value="default", key="custom_index_ns")
            else:
                index_namespace = ns_idx_sel

            chunk_size_val = st.number_input("Chunk Size", value=500, step=50)
            chunk_overlap_val = st.number_input("Chunk Overlap", value=50, step=10)

            if st.button("🚀 Index Document(s)", use_container_width=True):
                strategy_param = "hybrid" if "Hybrid" in strategy_choice else "fixed_overlap"
                req_params = {
                    "namespace": index_namespace,
                    "chunking_strategy": strategy_param,
                    "chunk_size": chunk_size_val,
                    "chunk_overlap": chunk_overlap_val,
                }
                files_payload = [("files", (f.name, f.getvalue(), f.type or "application/octet-stream")) for f in uploaded_files]

                with st.spinner("Processing & indexing vectors…"):
                    resp, err = api_post("/index", params=req_params, files=files_payload)

                if err:
                    st.error(f"Indexing Failed: {err}")
                else:
                    st.success(f"✅ Stored {resp['vectors_stored']:,} vectors in `{resp.get('namespace', index_namespace)}`!")

    # System Status Monitor
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3)
        if r.status_code == 200 and r.json().get("pipeline_ready"):
            st.caption("🟢 **Backend System:** Online & Ready")
        else:
            st.caption("🟡 **Backend System:** Initializing...")
    except Exception:
        st.caption("🔴 **Backend System:** Disconnected")

    # Golden Hit Rate @ 3 Evaluation panel
    st.markdown("**🎯 Golden Hit Rate @ 3**")
    st.caption("12 golden questions evaluated against Pinecone chunk IDs")

    col_disc, col_eval = st.columns(2)
    with col_disc:
        if st.button("🔍 Discover", use_container_width=True, key="btn_discover",
                     help="Embed golden answers → find correct chunk IDs in Pinecone"):
            with st.spinner("Discovering chunk IDs…"):
                resp, err = api_post("/golden/discover", json={})
            if err:
                st.error(f"Discover failed: {err}")
            else:
                discovered = resp.get("discovered", [])
                found = sum(1 for d in discovered if d.get("correct_chunk_id"))
                st.success(f"Mapped {found}/12 chunks")
    with col_eval:
        if st.button("▶ Evaluate", use_container_width=True, key="btn_evaluate",
                     help="Run all 12 questions through retriever and compute hit rate"):
            with st.spinner("Running evaluation…"):
                resp, err = api_get("/golden/evaluate", params={"use_reranker": str(use_reranker).lower()})
            if err:
                st.error(f"Evaluate failed: {err}")
            else:
                st.session_state["golden_eval"] = resp

    if "golden_eval" in st.session_state:
        ev = st.session_state["golden_eval"]
        hits = ev.get("hits", 0)
        total = ev.get("total", 0)
        pct = ev.get("rate_pct", 0.0)
        ev_reranked = ev.get("use_reranker", False)
        mode_label = "⚡ With Reranker" if ev_reranked else "📐 Semantic Only"
        hr_color = "#10a37f" if pct >= 70 else "#f59e0b" if pct >= 40 else "#ef4444"
        st.markdown(
            f'<div style="margin:6px 0;padding:10px 14px;border-radius:10px;'
            f'border:1px solid {hr_color};background:rgba(0,0,0,0.03);">'
            f'<span style="font-size:1.4rem;font-weight:700;color:{hr_color};">'
            f'{pct:.0f}%</span>'
            f'<span style="font-size:0.8rem;color:#888;margin-left:8px;">'
            f'{hits} / {total} questions</span><br>'
            f'<span style="font-size:0.75rem;color:#aaa;">{mode_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.expander("Per-question breakdown", expanded=False):
            for r in ev.get("results", []):
                if r.get("is_hit") is None:
                    icon = "⚠️"
                elif r["is_hit"]:
                    icon = "✅"
                else:
                    icon = "❌"
                st.markdown(
                    f"{icon} **{r['id']}** — `{r.get('correct_chunk_id', 'not mapped')}` "
                    f"in `{r.get('namespace', '')}`",
                    unsafe_allow_html=False,
                )


# ---------------------------------------------------------------------------
# Main ChatGPT Feed & Real-Time Interaction
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# Welcome Screen & ChatGPT Suggestion Cards if chat history is empty
if not st.session_state.messages:
    st.markdown(
        """
        <div style="text-align:center; margin: 40px 0 35px 0;">
            <div style="font-size:2.8rem; margin-bottom:8px;">🟢</div>
            <h1 style="font-size:2.2rem; font-weight:700; color:#0d0d0d; margin-bottom:6px;">
                What can I help with today?
            </h1>
            <p style="color:#676767; font-size:1rem;">
                Ask questions about your uploaded documents, tables, or reports.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Handle prompt suggestion click trigger
prompt_to_send = None
if "prompt_trigger" in st.session_state and st.session_state.prompt_trigger:
    prompt_to_send = st.session_state.prompt_trigger
    st.session_state.prompt_trigger = None

# Render ChatGPT Message Stream
for message in st.session_state.messages:
    avatar_icon = "🧑‍💻" if message["role"] == "user" else "🟢"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            latency_ms = message.get("latency_ms", 0.0)
            was_reranked = message.get("reranked", False)
            if latency_ms or was_reranked:
                lat_color = "#10a37f" if latency_ms < 1000 else "#f59e0b" if latency_ms < 3000 else "#ef4444"
                lat_label = f"{latency_ms:.0f} ms" if latency_ms < 1000 else f"{latency_ms/1000:.2f} s"
                reranker_badge = (
                    '<span style="background:rgba(0,0,0,0.04);color:#7c3aed;'
                    'border:1px solid #7c3aed;padding:3px 10px;border-radius:999px;'
                    'font-weight:600;font-size:0.78rem;margin-right:6px;">'
                    '⚡ Reranked'
                    '</span>'
                ) if was_reranked else ""
                st.markdown(
                    f'<div style="margin-top:8px;">'
                    f'{reranker_badge}'
                    f'<span style="background:rgba(0,0,0,0.04);color:{lat_color};'
                    f'border:1px solid {lat_color};padding:3px 10px;border-radius:999px;'
                    f'font-weight:600;font-size:0.78rem;">'
                    f'⏱ {lat_label}'
                    f'</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if message.get("sources"):
                with st.expander(f"📄 Source Context ({len(message['sources'])})", expanded=False):
                    for i, src in enumerate(message["sources"], 1):
                        score_pct = src["score"] * 100
                        st.markdown(
                            f'<div class="source-box">'
                            f'<strong>[{i}] {src["source"]}</strong> (Chunk #{src["chunk_index"]} · {score_pct:.1f}% Match)<br>'
                            f'<span style="color:#676767;">{src["text"]}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

# Fixed Bottom ChatGPT Input Bar (st.chat_input)
user_input = st.chat_input("Message ChatGPT...") or prompt_to_send

if user_input:
    # 1. Append User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_input)

    # 2. Query RAG Backend
    payload = {
        "question": user_input,
        "namespace": selected_namespace,
        "return_sources": show_sources,
        "use_reranker": use_reranker,
    }

    with st.chat_message("assistant", avatar="🟢"):
        message_placeholder = st.empty()
        with st.spinner("Retrieving vector context & generating response…"):
            resp, err = api_post("/chat", json=payload)

        if err:
            st.error(f"Error: {err}")
        else:
            answer_text = resp.get("answer", "No answer returned.")
            sources = resp.get("sources")
            latency_ms = resp.get("latency_ms", 0.0)
            was_reranked = resp.get("reranked", False)

            # Real-Time Word-by-Word Streaming Simulation
            full_response = ""
            words = answer_text.split(" ")
            for idx, word in enumerate(words):
                full_response += word + " "
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.02) # Fast real-time typing effect

            message_placeholder.markdown(full_response)

            if latency_ms or was_reranked:
                lat_color = "#10a37f" if latency_ms < 1000 else "#f59e0b" if latency_ms < 3000 else "#ef4444"
                lat_label = f"{latency_ms:.0f} ms" if latency_ms < 1000 else f"{latency_ms/1000:.2f} s"
                reranker_badge = (
                    '<span style="background:rgba(0,0,0,0.04);color:#7c3aed;'
                    'border:1px solid #7c3aed;padding:3px 10px;border-radius:999px;'
                    'font-weight:600;font-size:0.78rem;margin-right:6px;">'
                    '⚡ Reranked'
                    '</span>'
                ) if was_reranked else ""
                st.markdown(
                    f'<div style="margin-top:8px;">'
                    f'{reranker_badge}'
                    f'<span style="background:rgba(0,0,0,0.04);color:{lat_color};'
                    f'border:1px solid {lat_color};padding:3px 10px;border-radius:999px;'
                    f'font-weight:600;font-size:0.78rem;">'
                    f'⏱ {lat_label}'
                    f'</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if sources:
                with st.expander(f"📄 Source Context ({len(sources)})", expanded=False):
                    for i, src in enumerate(sources, 1):
                        score_pct = src["score"] * 100
                        st.markdown(
                            f'<div class="source-box">'
                            f'<strong>[{i}] {src["source"]}</strong> (Chunk #{src["chunk_index"]} · {score_pct:.1f}% Match)<br>'
                            f'<span style="color:#676767;">{src["text"]}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            # Store assistant response in session history
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response.strip(),
                "sources": sources,
                "latency_ms": latency_ms,
                "reranked": was_reranked,
            })
