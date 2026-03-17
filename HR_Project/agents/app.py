# Save this as receiver.py on your local PC
from fastapi import FastAPI, UploadFile, File
import uvicorn
import shutil

app = FastAPI()

@app.post("/upload")
async def receive_file(file: UploadFile = File(...)):
    with open(f"./{file.filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "filename": file.filename}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)