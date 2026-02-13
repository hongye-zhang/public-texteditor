# AI-Powered Text Editor (Prototype)

A prototype of an AI-centric document editor that integrates LLM-based editing directly into the writing workflow.
The system supports structured document editing, iterative refinement, and targeted modifications via natural language instructions.

This project aims to realise reliable document manipulation through explicit planning, constrained context extraction, and diff-based updates.

## 🏗️ Architecture

### Frontend Stack
- **Framework**: SvelteKit 2.x with TypeScript
- **Editor**: TipTap 2.x (ProseMirror-based)
- **Styling**: TailwindCSS 3.x
- **State Management**: Svelte stores
- **Build Tool**: Vite 6.x

### Backend Stack
- **Framework**: FastAPI (Python)
- **LLM Integration**: LangChain with OpenAI
- **Document Processing**: python-docx for Word document handling
- **API Architecture**: RESTful with Server-Sent Events (SSE) for streaming

### Core Components

```
├── llm-editor-chat/          # Main desktop application
│   ├── frontend/             # SvelteKit web interface
│   ├── backend/              # FastAPI Python backend
│   │   ├── features/
│   │   │   ├── chat/         # Chat and streaming endpoints
│   │   │   ├── document_editing/  # Document manipulation services
│   │   │   ├── intent_analysis/   # AI intent recognition
│   │   │   ├── llm/          # LLM service integration
│   │   │   └── processing/   # Content processing pipelines
│   │   └── app/
│   └── electron/             # Electron wrapper
├── llm-editor-chrome/        # Chrome extension version
└── editing/                  # Core editing algorithms
    ├── edit_planner.py       # Intelligent edit planning
    ├── document_editor.py    # Document manipulation
    └── diff_generator.py     # Change tracking
```

## Key Functions
- Hierarchical multi level intent routing (create/modify/Q&A/image) with confidence thresholding
- Token-efficient context extraction for targeted edits (windowed section selection)
- Diff-based structured updates to TipTap JSON (format-preserving)
- Streaming execution pipeline (SSE) with action events



## 🚀 Getting Started

### Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.9+
- **OpenAI API Key** (for LLM features)

### Installation

#### Desktop Application

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/public-texteditor.git
   cd public-texteditor/llm-editor-chat
   ```

2. **Set up the backend**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   # Create .env file in llm-editor-chat directory
   OPENAI_API_KEY=your_api_key_here
   OPENAI_CHAT_MODEL=gpt-4o-mini
   OPENAI_IMAGE_MODEL=dall-e-3
   ```

4. **Install frontend dependencies**
   ```bash
   cd ../frontend
   npm install
   ```

5. **Install Electron dependencies**
   ```bash
   cd ../electron
   npm install
   ```

6. **Start the development environment**
   ```bash
   # From llm-editor-chat directory
   
   llm-editor-chat\bats\backend.ps1
   llm-editor-chat\bats\frontend.ps1
   


**Note**: This project requires an OpenAI API key for AI features. API usage costs apply based on your OpenAI pricing plan.
