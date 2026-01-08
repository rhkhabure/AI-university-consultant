from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from parser import parse_pdf
import uvicorn

app = FastAPI()

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    temp_path = "uploaded.pdf"
    with open(temp_path, "wb") as f:
        f.write(contents)
    comments = parse_pdf(temp_path)
    return {"comments": comments[:50]}  # return first 50 for verification

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)