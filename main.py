import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from mangum import Mangum
from database import SessionLocal, Video, init_db

init_db()
app = FastAPI()
handler = Mangum(app) # Для Vercel

app.mount("/static", StaticFiles(directory="static"), name="static")
# ВАЖНО: На Vercel папка uploads будет работать только для чтения после деплоя.
# Для полноценной работы нужно будет подключить облако (S3/Supabase),
# но для структуры оставляем так:
if os.path.exists("uploads"):
    app.mount("/videos", StaticFiles(directory="uploads"), name="videos")

templates = Jinja2Templates(directory="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    videos = db.query(Video).all()
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/do-upload")
async def handle_upload(title: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1]
    file_name = f"{file_id}.{file_ext}"
    file_path = os.path.join("uploads", file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_video = Video(id=file_id, title=title, url=f"/videos/{file_name}")
    db.add(new_video)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/watch/{video_id}", response_class=HTMLResponse)
async def watch_video(request: Request, video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    return templates.TemplateResponse("watch.html", {"request": request, "video": video})
