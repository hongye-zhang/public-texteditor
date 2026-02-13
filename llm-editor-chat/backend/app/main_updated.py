from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.routers import examples, llm, text_selection, text_modification, document_structure, command_parsing, document_tree
from app.features.chat.router import router as chat_router
from app.logging_config import configure_logging

# 配置日志系统
configure_logging()

app = FastAPI(title="LLM Editor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # SvelteKit dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include existing routers
app.include_router(examples.router)
app.include_router(llm.router)
app.include_router(chat_router)

# Include new routers for advanced editing features
app.include_router(text_selection.router)
app.include_router(text_modification.router)
app.include_router(document_structure.router)
app.include_router(command_parsing.router)
app.include_router(document_tree.router)  # Add the new document tree router

@app.get("/")
async def root():
    return {"message": "Welcome to LLM Editor API"}

@app.get("/health")
async def health():
    return {"status": "ok"}
