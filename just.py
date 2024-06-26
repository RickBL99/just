import subprocess
import json
import os
import platform
import secrets
import logging
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import time

api = FastAPI()
templates = Jinja2Templates(directory="templates")
current_dir = os.getcwd()

# Ensure the uploaded_files directory exists
uploaded_files_dir = os.path.join(current_dir, "uploaded_files")
if not os.path.exists(uploaded_files_dir):
    os.makedirs(uploaded_files_dir)

logging.getLogger().handlers.clear()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

# Add a StreamHandler to log to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# GET ALL API >PY FILES
from api import upload
from api import getallmeta

logging.debug("Including upload router")
api.include_router(upload.router)

logging.debug("Including getallmeta router")
api.include_router(getallmeta.router)

# Mount static and uploaded_files directories
logging.debug("Mounting static directory")
api.mount('/static', StaticFiles(directory='static'), name='static')

logging.debug("Mounting uploaded_files directory")
api.mount("/uploaded_files", StaticFiles(directory='uploaded_files'), name="uploaded_files")

@api.get("/")
def form_post(request: Request):
    session_id = secrets.token_hex(16)
    logging.debug(f"Generated session ID: {session_id}")

    headers = {"Set-Cookie": f"session_id={session_id}; Max-Age=3600; Path=/"}

    response = templates.TemplateResponse("upload.html", {"request": request})
    response.headers["Set-Cookie"] = f"session_id={session_id}; Max-Age=3600; Path=/"

    # Log the details about the cookie set
    cookie_value = request.cookies.get('session_id')
    logging.debug(f"Cookie value before sending response: {cookie_value}")
    logging.debug(f"Cookie exists before sending response: {cookie_value is not None}")

    return response

@api.get("/check-cookie")
def check_cookie(request: Request):
    cookie_value = request.cookies.get('session_id')
    logging.debug(f"Cookie value on subsequent request: {cookie_value}")
    logging.debug(f"Cookie exists on subsequent request: {cookie_value is not None}")

    return {"cookie_value": cookie_value, "cookie_exists": cookie_value is not None}

@api.get("/file-check", response_class=HTMLResponse)
def file_check(request: Request):
    session_id = request.cookies.get('session_id')
    if not session_id:
        return templates.TemplateResponse("file_check.html", {"request": request, "files": [], "error": "No session ID found."})

    directory_path = os.path.join("uploaded_files", session_id)
    if not os.path.exists(directory_path):
        return templates.TemplateResponse("file_check.html", {"request": request, "files": [], "error": f"No files found for session ID: {session_id}"})

    files = os.listdir(directory_path)
    logging.debug(f"Files in session directory {directory_path}: {files}")

    return templates.TemplateResponse("file_check.html", {"request": request, "files": files, "error": None})



@api.post("/result", response_class=HTMLResponse)
async def index(request: Request, file: UploadFile = File(...)):
    # Save the uploaded file
    upload_dir = os.path.join(current_dir, "uploaded_files")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    logging.debug(f"Saving file to: {file_path}")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    logging.debug(f"File {file.filename} saved successfully")

    # Add a 5-second delay
    logging.debug("Waiting for 5 seconds to ensure file is fully saved")
    time.sleep(5)
    logging.debug("Completed waiting for 5 seconds")

    # Check if the file exists
    if not os.path.isfile(file_path):
        logging.debug(f"File {file_path} does not exist after 5 seconds")
        return HTMLResponse(content=f"Error: File {file_path} does not exist", status_code=404)
    
    logging.debug(f"File {file_path} confirmed to exist")

    # Determine the path to exiftool
    def is_executable(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    exiftool_path = "exiftool"  # Default to using the system-installed exiftool
    if not is_executable(exiftool_path):
        exiftool_path = os.path.join(current_dir, "tools", "exiftool")
        # Ensure exiftool is executable
        if platform.system() != "Windows":
            subprocess.run(["chmod", "+x", exiftool_path])

    logging.debug(f"Using exiftool path: {exiftool_path}")
    logging.debug(f"Running exiftool command on file {file_path}")

    try:
        exiftool_output = subprocess.check_output([exiftool_path, "-j", file_path])
    except subprocess.CalledProcessError as e:
        logging.debug(f"Exiftool error: {e.output.decode()}")
        return HTMLResponse(content=f"Error: Exiftool failed to retrieve metadata", status_code=500)

    exif_data = json.loads(exiftool_output)

    table_rows = ""
    for item in exif_data[0].items():
        table_rows += f"<tr><td>{item[0]}</td><td>{item[1]}</td></tr>"
    table_html = f"<table class='table'>{table_rows}</table>"

    logging.debug("Metadata extraction successful")

    return templates.TemplateResponse("index.html", {"request": request, "table_html": table_html, "filename": file.filename})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("just:api", host="0.0.0.0", port=8000)

