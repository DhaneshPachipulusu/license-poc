"""
Minimal test version - Use this to verify your server works
"""
from fastapi import FastAPI

app = FastAPI(title='License Server Test')

@app.get("/")
def root():
    return {"status": "ok", "message": "License server is running!"}

@app.get("/test")
def test():
    return {"test": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    