import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import tempfile
import shutil

load_dotenv()

OPENROUTER_API_BASE = os.getenv("OPENROUTER_API_BASE") or os.getenv(
    "OPENAI_API_BASE", "https://openrouter.ai/api/v1"
)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

app = FastAPI(
    title="PDF Chat API",
    description="Chat with your PDF using Retrieval Augmented Generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qa_chain = None
vectorstore = None

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def load_and_process_pdf(pdf_path: str):
    global qa_chain, vectorstore
    
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)
    
    embeddings = OpenAIEmbeddings(
        base_url=OPENROUTER_API_BASE,
        model="openai/text-embedding-3-small",
        api_key=OPENROUTER_API_KEY,
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    llm = ChatOpenAI(
        temperature=0,
        model="openai/gpt-4o-mini",
        base_url=OPENROUTER_API_BASE,
        api_key=OPENROUTER_API_KEY,
    )
    
    prompt = ChatPromptTemplate.from_template("""Answer the question based only on the following context:

{context}

Question: {question}

Answer: """)
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    
    qa_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return len(chunks)

@app.get("/")
def root():
    return {"status": "running", "message": "PDF Chat API is ready"}

@app.get("/status")
def get_status():
    return {
        "pdf_loaded": qa_chain is not None,
        "message": "PDF is loaded and ready for questions" if qa_chain else "No PDF loaded yet. Please upload a PDF first."
    }

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        num_chunks = load_and_process_pdf(tmp_path)
        os.unlink(tmp_path)
        
        return {
            "message": f"PDF '{file.filename}' processed successfully",
            "chunks_created": num_chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/ask", response_model=AnswerResponse)
def ask_question(req: QuestionRequest):
    if qa_chain is None:
        raise HTTPException(
            status_code=400, 
            detail="No PDF has been loaded. Please upload a PDF first using the /upload endpoint."
        )
    
    try:
        result = qa_chain.invoke(req.question)
        return {"answer": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.on_event("startup")
async def startup_event():
    default_pdf = os.path.join(os.path.dirname(__file__), "documents", "document.pdf")
    if os.path.exists(default_pdf):
        try:
            load_and_process_pdf(default_pdf)
            print(f"Loaded default PDF: {default_pdf}")
        except Exception as e:
            print(f"Could not load default PDF: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
