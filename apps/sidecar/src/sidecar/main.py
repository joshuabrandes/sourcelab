import uvicorn
from fastapi import FastAPI

app = FastAPI(title="SourceLab Sidecar", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

def main():
    uvicorn.run("sidecar.main:app", host="127.0.0.1", port=8000, reload=False)
