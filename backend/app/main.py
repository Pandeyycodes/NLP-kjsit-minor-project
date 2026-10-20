from fastapi import FastAPI

app = FastAPI(title="Samjho")


@app.get("/")
def root():
    return {"project": "Samjho", "message": "Samjho backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}
