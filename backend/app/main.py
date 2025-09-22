from fastapi import FastAPI, UploadFile, Form
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello Steganografi!"}

@app.post("/embed")
async def embed(file: UploadFile, secret: UploadFile, key: str = Form(...)):
    # TODO: panggil fungsi steganografi
    return {"status": "success", "key": key}

@app.post("/extract")
async def extract(file: UploadFile, key: str = Form(...)):
    # TODO: panggil fungsi ekstraksi
    return {"status": "extracted", "key": key}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
