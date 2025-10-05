# MP3 Steganography using n-LSB Method
## Description
This program can take any file to be embedded to a MP3 file by taking each bit of the file into the n-LSB of each un-reserved bytes in the MP3 file.
## Tech Stack
* Docker, as containerization
* Reast, as frontend framework
* Python (Uvicorn & FastAPI), as API management and bussiness logic
## Dependencies
* fastapi==0.117.1
* numpy==1.26.4
* pydub==0.25.1
* python-magic==0.4.27
* uvicorn==0.36.0
## How to Run Program
1. Build and run using docker.
   ```bash
   docker compose up --build
2. Open the frontend service in ```localhost:3000```
3. You can choose to embed or extracting messages.
