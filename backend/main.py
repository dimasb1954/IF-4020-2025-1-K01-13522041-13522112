from fastapi import FastAPI, UploadFile, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from io import BytesIO
import os
from app.tugas2 import embed_message, extract_message

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Hello Steganografi!"}

# ============== INSERT (embed) ==============
@app.post("/embed")
async def embed(
    cover: UploadFile,                       # file mp3 asli
    message: UploadFile,                     # file txt
    useEncryption: str = Form(...),          # "true" / "false"
    useRandomStart: str = Form(...),         # "true" / "false"
    nLSB: int = Form(...),                   # jumlah bit
    seed: str = Form("")                     # kunci/seed opsional
):
    try:
        # Save temporary files
        temp_audio = "temp_audio.mp3"
        temp_message = "temp_message.txt"
        
        # Save uploaded files temporarily
        with open(temp_audio, "wb") as audio_file:
            audio_file.write(await cover.read())
        with open(temp_message, "wb") as message_file:
            message_file.write(await message.read())
        
        # Process embedding
        is_encrypt = useEncryption.lower() == "true"
        output_bytes = embed_message(
            audio_path=temp_audio,
            message_path=temp_message,
            is_encrypt=is_encrypt,
            key=seed if is_encrypt else ""
        )
        
        # Return MP3 file
        return StreamingResponse(
            BytesIO(output_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=stego_{cover.filename}"
            }
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============== EXTRACT =====================
@app.post("/extract")
async def extract(
    stego: UploadFile,               # file stego mp3
    seed: str = Form("")             # kunci stego
):
    try:
        # Save temporary file
        temp_stego = "temp_stego.mp3"
        
        # Save uploaded file temporarily
        with open(temp_stego, "wb") as stego_file:
            stego_file.write(await stego.read())
        
        # Extract message
        is_decrypt = bool(seed)
        extracted_bytes = extract_message(
            stego_path=temp_stego,
            is_decrypt=is_decrypt,
            key=seed if is_decrypt else ""
        )
        
        # Return extracted file
        return Response(
            content=extracted_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=extracted_message.txt"
            }
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)