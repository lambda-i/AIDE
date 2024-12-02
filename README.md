# AIDE

## Directory Structure
```md
ai-disease-evaluator/
├─ src/
│  ├── components/      # Reusable components for the UI (Streamlit)
│  ├── pages/           # Main pages (Q&A, Results, etc.)
│  ├── services/        # API calls and logic for MongoDB, AI model integration, etc.
│  ├── utils/           # Helper functions, shared utilities
│  ├── config/          # Configuration files (API keys, constants)
│  ├── mongodb/         # MongoDB utilities (CRUD operations)
│  ├── rag_framework/   # RAG-based medication recommendation logic
│  ├── location/        # Google Maps API integration
│  ├── ai_model/        # RealTime API integration
│  ├── schemas.py       # Data schemas for validation and information collection
│  ├── App.py           # Streamlit entry point
├─ .env.local           # Local environment variables
├─ .env.local.dist      # Template for sharing environment variables
├─ requirements.txt     # Python dependencies
├─ README.md            # Main project instructions
```