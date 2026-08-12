"""
RAG Application — Streamlit Frontend
======================================
A beautiful, light-themed frontend for the FastAPI RAG backend.

Pages:
    💬 Chat        — Ask questions and get AI-generated answers
    📂 Index Docs  — Upload and index one or more documents
"""

import time
import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = "http://localhost:8000"
SUPPORTED_TYPES = ["txt", "md", "pdf", "docx", "csv", "json", "html", "htm"]

# ---------------------------------------------------------------------------
# Page config & global styles
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="RAG Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Light background ── */
    .stApp {
        background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 50%, #f0f9ff 100%);
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8f5ff 100%);
        border-right: 1px solid #e2d9f3;
    }

    /* ── Primary button ── */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed 0%, #9d71fa 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0.55rem 1.4rem;
        transition: all 0.25s ease;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 22px rgba(124, 58, 237, 0.45);
        background: linear-gradient(135deg, #6d28d9 0%, #8b5cf6 100%);
    }
    .stButton > button:active {
        transform: translateY(0);
    }

    /* ── Chat message bubbles ── */
    .user-bubble {
        background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
        border: 1px solid #c4b5fd;
        border-radius: 18px 18px 4px 18px;
        padding: 14px 18px;
        margin: 8px 0 8px 40px;
        color: #3b0764;
        font-size: 0.95rem;
        line-height: 1.6;
        animation: fadeSlideIn 0.3s ease;
    }
    .assistant-bubble {
        background: linear-gradient(135deg, #ffffff 0%, #f8faff 100%);
        border: 1px solid #e2d9f3;
        border-radius: 18px 18px 18px 4px;
        padding: 14px 18px;
        margin: 8px 40px 8px 0;
        color: #1e293b;
        font-size: 0.95rem;
        line-height: 1.7;
        box-shadow: 0 2px 8px rgba(124, 58, 237, 0.08);
        animation: fadeSlideIn 0.3s ease;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #faf5ff 100%);
        border: 1px solid #e2d9f3;
        border-radius: 14px;
        padding: 22px 24px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(124, 58, 237, 0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 28px rgba(124, 58, 237, 0.18);
        border-color: #a78bfa;
    }
    .metric-value {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #7c3aed, #2563eb);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label {
        font-size: 0.82rem;
        color: #64748b;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
    }

    /* ── Source card ── */
    .source-card {
        background: #ffffff;
        border: 1px solid #e2d9f3;
        border-left: 4px solid #7c3aed;
        border-radius: 8px;
        padding: 14px 16px;
        margin: 6px 0;
        font-size: 0.87rem;
        color: #475569;
        box-shadow: 0 1px 4px rgba(124, 58, 237, 0.06);
    }
    .source-title {
        color: #7c3aed;
        font-weight: 600;
        margin-bottom: 6px;
    }

    /* ── Hit rate bar ── */
    .hit-bar-container {
        background: #ede9fe;
        border-radius: 999px;
        height: 8px;
        overflow: hidden;
        margin: 6px 0;
    }
    .hit-bar-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #7c3aed, #9d71fa);
        transition: width 0.6s ease;
    }

    /* ── Upload area enhancement ── */
    [data-testid="stFileUploader"] {
        border: 2px dashed #c4b5fd;
        border-radius: 14px;
        padding: 10px;
        background: #faf5ff;
        transition: border-color 0.2s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #7c3aed;
        background: #f5f3ff;
    }

    /* ── Animations ── */
    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse-ring {
        0%   { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.4); }
        70%  { box-shadow: 0 0 0 10px rgba(124, 58, 237, 0); }
        100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0); }
    }

    /* ── Divider ── */
    hr {
        border: none;
        border-top: 1px solid #e2d9f3;
        margin: 1.5rem 0;
    }

    /* ── Input text area ── */
    .stTextArea > div > div > textarea,
    .stTextInput > div > div > input {
        background: #ffffff !important;
        border: 1px solid #c4b5fd !important;
        color: #1e293b !important;
        border-radius: 10px !important;
    }
    .stTextArea > div > div > textarea:focus,
    .stTextInput > div > div > input:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.15) !important;
    }

    /* ── Select box ── */
    .stSelectbox > div > div {
        background: #ffffff !important;
        border: 1px solid #c4b5fd !important;
        border-radius: 10px !important;
        color: #1e293b !important;
    }

    /* ── Success / Error alerts ── */
    .stSuccess { border-radius: 10px !important; }
    .stError   { border-radius: 10px !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #c4b5fd; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #7c3aed; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 20px 0 10px 0;">
            <div style="font-size:3rem;">🧠</div>
            <div style="font-size:1.3rem; font-weight:700;
                        background: linear-gradient(135deg,#7c3aed,#2563eb);
                        -webkit-background-clip:text;
                        -webkit-text-fill-color:transparent;
                        background-clip:text;">
                RAG Assistant
            </div>
            <div style="font-size:0.75rem; color:#64748b; margin-top:4px;">
                Powered by Pinecone · Groq · BGE
            </div>
        </div>
        <hr>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigate",
        options=["💬 Chat", "📂 Index Documents"],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Backend health indicator
    with st.container():
        try:
            r = httpx.get(f"{API_BASE}/health", timeout=3)
            if r.status_code == 200 and r.json().get("pipeline_ready"):
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:8px;">'
                    '<div style="width:10px;height:10px;border-radius:50%;'
                    'background:#16a34a;animation:pulse-ring 2s infinite;"></div>'
                    '<span style="font-size:0.8rem;color:#16a34a;font-weight:600;">Backend Online</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:8px;">'
                    '<div style="width:10px;height:10px;border-radius:50%;background:#d97706;"></div>'
                    '<span style="font-size:0.8rem;color:#d97706;font-weight:600;">Pipeline Initializing…</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )
        except Exception:
            st.markdown(
                '<div style="display:flex;align-items:center;gap:8px;">'
                '<div style="width:10px;height:10px;border-radius:50%;background:#dc2626;"></div>'
                '<span style="font-size:0.8rem;color:#dc2626;font-weight:600;">Backend Offline</span>'
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div style="position:fixed;bottom:20px;left:20px;right:20px;
                    font-size:0.72rem;color:#94a3b8;text-align:center;">
            Start backend: <code style="background:#ede9fe;color:#7c3aed;
            padding:2px 6px;border-radius:4px;">uvicorn api:app --port 8000</code>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_post(path: str, **kwargs):
    """POST to the FastAPI backend with a reasonable timeout."""
    try:
        r = httpx.post(f"{API_BASE}{path}", timeout=120, **kwargs)
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, "Cannot connect to the backend. Is `uvicorn main:app --port 8000` running?"
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = exc.response.text or str(exc)
        return None, f"API error {exc.response.status_code}: {detail}"
    except Exception as exc:
        return None, str(exc)


def api_get(path: str):
    """GET from the FastAPI backend."""
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=30)
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, "Cannot connect to the backend. Is `uvicorn main:app --port 8000` running?"
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = exc.response.text or str(exc)
        return None, f"API error {exc.response.status_code}: {detail}"
    except Exception as exc:
        return None, str(exc)


def render_hit_rate(hit_rate: dict):
    """Render a compact hit-rate bar inside an expander."""
    rate = hit_rate.get("rate", 0.0)
    hits = hit_rate.get("hits", 0)
    total = hit_rate.get("total", 0)
    threshold = hit_rate.get("threshold", 0.5)
    pct = int(rate * 100)

    st.markdown(
        f"""
        <div style="font-size:0.82rem;color:#64748b;margin-bottom:4px;">
            Retrieval Hit Rate &nbsp;
            <span style="color:#7c3aed;font-weight:600;">{hits}/{total} chunks</span>
            &nbsp;·&nbsp; threshold ≥ {threshold}
        </div>
        <div class="hit-bar-container">
            <div class="hit-bar-fill" style="width:{pct}%;"></div>
        </div>
        <div style="font-size:0.78rem;color:#94a3b8;text-align:right;">{pct}%</div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page: Chat
# ---------------------------------------------------------------------------

if page == "💬 Chat":
    st.markdown(
        """
        <h1 style="font-size:2rem;font-weight:700;margin-bottom:0;
                   background:linear-gradient(135deg,#7c3aed,#2563eb);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;">
            💬 Chat with your Documents
        </h1>
        <p style="color:#64748b;font-size:0.92rem;margin-top:6px;">
            Ask any question — the AI retrieves relevant context from your indexed documents.
        </p>
        <hr>
        """,
        unsafe_allow_html=True,
    )

    # Chat history stored in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display existing messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-bubble">🧑‍💻 &nbsp;{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="assistant-bubble">🤖 &nbsp;{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
            if msg.get("hit_rate"):
                with st.expander("📊 Retrieval metrics", expanded=False):
                    render_hit_rate(msg["hit_rate"])
                    if msg.get("scores"):
                        st.caption(f"Similarity scores: {msg['scores']}")
            if msg.get("sources"):
                with st.expander(f"📄 Sources ({len(msg['sources'])})", expanded=False):
                    for i, src in enumerate(msg["sources"], 1):
                        st.markdown(
                            f'<div class="source-card">'
                            f'<div class="source-title">'
                            f'[{i}] {src["source"]} '
                            f'· chunk #{src["chunk_index"]} · score {src["score"]:.4f}</div>'
                            f'<span style="color:#475569;">{src["text"]}</span>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

    # Input area
    with st.container():
        col1, col2 = st.columns([5, 1])
        with col1:
            question = st.text_area(
                "Your question",
                placeholder="e.g. What is the main topic of the uploaded documents?",
                height=90,
                label_visibility="collapsed",
                key="chat_input",
            )
        with col2:
            show_sources = st.checkbox("Show sources", value=False)
            send_clicked = st.button("Send ➤", use_container_width=True)

    if send_clicked and question.strip():
        # Append user message
        st.session_state.messages.append({"role": "user", "content": question.strip()})

        with st.spinner("🔍 Retrieving context & generating answer…"):
            data, error = api_post(
                "/chat",
                json={
                    "question": question.strip(),
                    "return_sources": show_sources,
                },
            )

        if error:
            st.error(f"❌ {error}")
        else:
            answer = data.get("answer", "No answer returned.")
            assistant_msg = {
                "role": "assistant",
                "content": answer,
                "hit_rate": data.get("hit_rate"),
                "scores": data.get("scores"),
                "sources": data.get("sources") if show_sources else None,
            }
            st.session_state.messages.append(assistant_msg)
            st.rerun()

    elif send_clicked and not question.strip():
        st.warning("⚠️ Please enter a question before sending.")

    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear conversation"):
            st.session_state.messages = []
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Index Documents
# ---------------------------------------------------------------------------

elif page == "📂 Index Documents":
    st.markdown(
        """
        <h1 style="font-size:2rem;font-weight:700;margin-bottom:0;
                   background:linear-gradient(135deg,#7c3aed,#2563eb);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                   background-clip:text;">
            📂 Index Documents
        </h1>
        <p style="color:#64748b;font-size:0.92rem;margin-top:6px;">
            Upload one or more documents to add them to the vector database.
            Supported formats: <strong style="color:#7c3aed;">.txt · .md · .pdf · .docx · .csv · .json · .html · .htm</strong>
        </p>
        <hr>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Drop your documents here",
        type=SUPPORTED_TYPES,
        accept_multiple_files=True,
        help="You can select multiple files at once. All formats listed above are supported.",
    )

    if uploaded_files:
        st.markdown(
            f"<p style='color:#64748b;font-size:0.87rem;'>"
            f"📎 {len(uploaded_files)} file(s) selected:</p>",
            unsafe_allow_html=True,
        )
        for f in uploaded_files:
            size_kb = round(len(f.getvalue()) / 1024, 1)
            st.markdown(
                f"<div style='font-size:0.85rem;color:#1e293b;padding:3px 0;'"
                f" background:#f8faff;border-radius:6px;'>"
                f"&nbsp;&nbsp;📄 <strong>{f.name}</strong>"
                f"<span style='color:#94a3b8;'> — {size_kb} KB</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col_btn, col_ns = st.columns([2, 3])
        with col_ns:
            namespace = st.text_input(
                "Pinecone namespace",
                value="default",
                help="Optionally organise vectors into a named namespace.",
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            index_clicked = st.button("⚡ Index Documents", use_container_width=True)

        if index_clicked:
            progress = st.progress(0, text="Preparing upload…")

            # Build multipart payload
            files_payload = []
            for f in uploaded_files:
                files_payload.append(("files", (f.name, f.getvalue(), f.type or "application/octet-stream")))

            progress.progress(25, text="Uploading to backend…")

            try:
                r = httpx.post(
                    f"{API_BASE}/index",
                    files=files_payload,
                    params={"namespace": namespace},
                    timeout=300,
                )
                progress.progress(75, text="Embedding & indexing vectors…")
                time.sleep(0.4)
                progress.progress(100, text="Done!")
                time.sleep(0.3)
                progress.empty()

                if r.status_code == 200:
                    resp = r.json()
                    st.success(
                        f"✅ {resp['message']}  \n"
                        f"**{resp['vectors_stored']:,}** vectors stored in namespace `{namespace}`."
                    )
                    st.balloons()
                else:
                    detail = r.json().get("detail", r.text)
                    st.error(f"❌ API error {r.status_code}: {detail}")

            except httpx.ConnectError:
                progress.empty()
                st.error("❌ Cannot connect to the backend. Is `uvicorn api:app --port 8000` running?")
            except Exception as exc:
                progress.empty()
                st.error(f"❌ Unexpected error: {exc}")

    else:
        st.markdown(
            """
            <div style="text-align:center;padding:60px 20px;
                        border:2px dashed #c4b5fd;border-radius:16px;
                        background:#faf5ff;color:#94a3b8;font-size:0.95rem;">
                <div style="font-size:3rem;margin-bottom:12px;">📁</div>
                <strong style="color:#7c3aed;">No files selected</strong><br>
                Use the uploader above to choose one or more documents.
            </div>
            """,
            unsafe_allow_html=True,
        )
