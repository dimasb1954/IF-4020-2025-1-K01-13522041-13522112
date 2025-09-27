from fastapi import FastAPI, UploadFile, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from io import BytesIO
import os
from app.tugas2 import embed_message, extract_message, calculatePSNR

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
    message: UploadFile,                     # file txt/file lain
    useEncryption: str = Form(...),          # "true" / "false"
    useRandomStart: str = Form(...),         # "true" / "false"
    nLSB: int = Form(...),                   # jumlah bit LSB yang digunakan (1-8)
    seed: str = Form("")                     # kunci/seed untuk enkripsi dan random start
):
    try:
        # Save temporary files
        temp_audio = "temp_audio.mp3"
        temp_message = "temp_message.bin"
        
        # Save uploaded files temporarily
        with open(temp_audio, "wb") as audio_file:
            audio_file.write(await cover.read())
        with open(temp_message, "wb") as message_file:
            message_file.write(await message.read())
        
        try:
            # Process embedding
            is_encrypt = useEncryption.lower() == "true"
            is_random = useRandomStart.lower() == "true"
            output_bytes = embed_message(
                audio_path=temp_audio,
                message_path=temp_message,
                is_encrypt=is_encrypt,
                key=seed,
                is_random=is_random,
                n_LSB=nLSB
            )
            
            # Save temporary stego file to calculate PSNR
            temp_stego = "temp_stego.mp3"
            with open(temp_stego, "wb") as stego_file:
                stego_file.write(output_bytes)

            try:
                # Return MP3 file and PSNR value
                return {
                    "file": StreamingResponse(
                        BytesIO(output_bytes),
                        media_type="audio/mpeg",
                        headers={
                            "Content-Disposition": f"attachment; filename=stego_{cover.filename}"
                        }
                    ),
                }
            finally:
                # Clean up temporary stego file
                if os.path.exists(temp_stego):
                    os.remove(temp_stego)
        finally:
            # Clean up temporary files
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            if os.path.exists(temp_message):
                os.remove(temp_message)

    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============== EXTRACT =====================
@app.post("/extract")
async def extract(
    stego: UploadFile,                      # file stego mp3
    seed: str = Form("")                    # kunci untuk dekripsi dan random start
):
    try:
        # Save temporary file
        temp_stego = "temp_stego.mp3"
        
        # Save uploaded file temporarily
        with open(temp_stego, "wb") as stego_file:
            stego_file.write(await stego.read())
        
        try:
            # Extract message
            message_bytes, mime_type, extension = extract_message(
                stego_path=temp_stego,
                key=seed
            )
            
            # Return extracted file with proper mime type and extension
            return Response(
                content=message_bytes,
                media_type=mime_type,
                headers={
                    "Content-Disposition": f"attachment; filename=extracted_message{extension}"
                }
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_stego):
                os.remove(temp_stego)

    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/calculate")
async def calculate(
    cover: UploadFile,   # file mp3 asli
    stego: UploadFile    # file mp3 stego
):
    try:
        temp_cover = "temp_cover.mp3"
        temp_stego = "temp_stego.mp3"

        # simpan file
        with open(temp_cover, "wb") as f:
            f.write(await cover.read())
        with open(temp_stego, "wb") as f:
            f.write(await stego.read())

        try:
            psnr_value = calculatePSNR(temp_cover, temp_stego)
            return {"psnr": psnr_value}
        finally:
            if os.path.exists(temp_cover):
                os.remove(temp_cover)
            if os.path.exists(temp_stego):
                os.remove(temp_stego)

    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
