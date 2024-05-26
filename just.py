import subprocess
import json
import os
import platform
import secrets
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

api = FastAPI()
templates = Jinja2Templates(directory="templates")
current_dir = os.getcwd()

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
    logging.info(f"Generated session ID: {session_id}")
    try:
        headers = {"Set-Cookie": f"session_id={session_id}; Max-Age=3600; Path=/"}
    except Exception as e:
        logging.error(f"Error adding cookie: {e}")

    logging.info("Added the cookie.")
    logging.info(f"Session ID: {session_id}")

    cookie_value = request.cookies.get('session_id')
    logging.info(f"Cookie value: {cookie_value}")
    logging.info(f"Cookie exists: {cookie_value is not None}")

    return templates.TemplateResponse("upload.html", {"request": request}, headers=headers)

@api.get("/result", response_class=HTMLResponse)
async def index(request: Request):
    filename = "z2084.jpg"  # Example filename, change it to the actual file you are working with

    # Determine the path to exiftool
    def is_executable(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    exiftool_path = "exiftool"  # Default to using the system-installed exiftool
    if not is_executable(exiftool_path):
        exiftool_path = os.path.join(current_dir, "tools", "exiftool")
        # Ensure exiftool is executable
        if platform.system() != "Windows":
            subprocess.run(["chmod", "+x", exiftool_path])

    # Check if the file exists
    file_path = os.path.join(current_dir, "static", filename)
    if not os.path.isfile(file_path):
        logging.error(f"File {file_path} does not exist")
        return HTMLResponse(content=f"Error: File {file_path} does not exist", status_code=404)

    logging.info(f"Using exiftool path: {exiftool_path}")
    logging.info(f"Running exiftool command on file {file_path}")

    try:
        exiftool_output = subprocess.check_output([exiftool_path, "-j", file_path])
    except subprocess.CalledProcessError as e:
        logging.error(f"Exiftool error: {e.output.decode()}")
        return HTMLResponse(content=f"Error: Exiftool failed to retrieve metadata", status_code=500)
    
    exif_data = json.loads(exiftool_output)
    
    table_rows = ""
    for item in exif_data[0].items():
        table_rows += f"<tr><td>{item[0]}</td><td>{item[1]}</td></tr>"
    table_html = f"<table class='table'>{table_rows}</table>"
    
    return templates.TemplateResponse("index.html", {"request": request, "table_html": table_html, "filename": filename})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("just:api", host="0.0.0.0", port=8000)
