# MultiTool-LangGraph-RAG-Agent

An AI-powered **multi-tool agent** built with **LangGraph** and **LangChain**, supporting:

- 🔹 **PDF Question Answering (RAG)** with PostgreSQL + pgvector  
- 🔹 **OCR** for low-text or image-heavy PDF pages (via Tesseract)  
- 🔹 **External tools**:  
  - Crypto price fetcher (CoinMarketCap API)  
  - Tavily web search  
- 🔹 **Persistent memory** with PostgreSQL and session management  
- 🔹 **Structured logging** for debugging and monitoring  

---

## 📌 Features

1. **Multi-Tool Agent**  
   Uses LangGraph to create an agent capable of handling multiple tools for reasoning and action execution.

2. **RAG for PDFs**  
   - Extracts text from PDFs using LangChain loaders  
   - Automatically detects low-text pages and applies OCR  
   - Stores vector embeddings in PostgreSQL + pgvector  
   - Enables semantic search and conversational question answering

3. **External Tools**  
   - **Tavily Search**: Retrieves web search results  
   - **Crypto Price Fetcher**: Provides real-time cryptocurrency prices via CoinMarketCap API  

4. **Persistence & Memory**  
   - Stores conversation history in PostgreSQL for persistence  
   - Tracks sessions with UUID-based management  

5. **Robust Logging and Error Handling**  
   - Comprehensive logging for debugging and monitoring  
   - Graceful error handling with automatic recovery  

---
