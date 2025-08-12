# MultiTool-LangGraph-RAG-Agent

An AI-powered **multi-tool agent** built with **LangGraph** and **LangChain**, supporting:

- 🔹 **PDF Question Answering (RAG)** with **PostgreSQL + pgvector**  
- 🔹 **OCR** for low-text or image-heavy PDF pages (via **Tesseract**)  
- 🔹 **External tools**:  
  - Crypto price fetcher (CoinMarketCap API)  
  - Tavily web search  
  - Custom RAG QA tool for indexed PDFs  
- 🔹 **Persistent memory** with PostgreSQL and session management  
- 🔹 **JWT authentication + Streamlit UI** (login/signup + streaming chat)  
- 🔹 **Structured logging** for debugging and monitoring

---

## 📌 Features (summary)

1. **Multi-Tool Agent**  
   Uses LangGraph to construct an agent that can call multiple tools (get_price, Tavily search, RAG QA) and handle tool results in a reasoning loop.

2. **RAG for PDFs**  
   - Load PDF pages via LangChain loaders  
   - Detect pages with low extracted text, convert to images and OCR them (Tesseract)  
   - Create documents, split into chunks and index into pgvector in PostgreSQL  
   - Enable conversational retrieval (ConversationalRetrievalChain)

3. **External Tools**  
   - **Tavily**: web search integration  
   - **CoinMarketCap**: crypto price fetching via API  
   - Custom `rag_qa` tool that queries the RAG index for PDF-based answers

4. **Persistence & Memory**  
   - Conversation/session persistence via LangGraph Checkpoints backed by PostgreSQL (async saver)  
   - Session IDs tracked via UUID (Streamlit session_state + API support)

5. **Authentication & UI**  
   - `auth.py`: SQLAlchemy user model, password hashing (bcrypt via `passlib`), JWT token generation/validation  
   - `auth_app.py` (Streamlit): signup/login UI that stores JWT in session_state  
   - `pages/chatbot.py` (Streamlit): streaming chat frontend that consumes `/chat/stream`

6. **Logging & Error Handling**  
   - Structured logging written to `logs/` (e.g. `logs/api.log`, `logs/app.log`)  
   - Graceful error reporting and helpful log lines (with `api_path` extra metadata)

---

## 📂 Project structure (key files)

```
├── api.py # FastAPI app (endpoints: /signup, /token, /chat, /chat/stream)
├── auth.py # Auth logic (SQLAlchemy user model, JWT, password hashing)
├── auth_app.py # Streamlit login/register page (client)
├── pages/
│ └── chatbot.py # Streamlit chat frontend (streams from /chat/stream)
├── graph.py # async agent wrapper used by api.py (provide abot there)
├── tools/
│ ├── tools.py # Tools exposed to the agent (get_price, safe_tavily, rag_qa)
│ └── rag_tool.py # PDF loading, OCR, chunking, embedding, PGVector setup
├── requirements.txt # Python deps 
├── .env # environment variables (not committed)
└── logs/ # runtime logs

```