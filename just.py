from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import subprocess
import json
import os
import platform
import secrets
import logging

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

api.include_router(upload.router)


# MOUNT PATHS

static_dir = os.path.join(current_dir, "static")
upload_dir = os.path.join(current_dir, "uploaded_files")

api.mount("/static", StaticFiles(directory=static_dir), name="static")
api.mount("/uploaded_files", StaticFiles(directory=upload_dir), name="uploaded_files")


# APPLICATION API

@api.get("/")
def form_post(request: Request):

    # Generate a secure random session ID
    session_id = secrets.token_hex(16)

    logging.info(f"Generated session ID: {session_id}")

    try:
        headers = {"Set-Cookie": f"session_id={session_id}; Max-Age=3600; Path=/"}
    except Exception as e:
        logging.error(f"Error adding cookie: {e}")

    logging.info("Added the cookie.")
    logging.info(f"Session ID: {session_id}")

    # Get the value of the session ID cookie
    cookie_value = request.cookies.get('session_id')
    logging.info(f"Cookie value: {cookie_value}")
    logging.info(f"Cookie exists: {cookie_value is not None}")

    # Return a TemplateResponse object that uses the upload.html template
    return templates.TemplateResponse("upload.html", {"request": request}, headers=headers)


@api.get("/result", response_class=HTMLResponse)
async def index(request: Request):
    filename = "test.jpg"
    
    # Run exiftool command to fetch all exif information
    logging.info(f"Running exiftool command on file {filename}")
    exiftool_output = subprocess.check_output(["exiftool", "-j", f"static/{filename}"])
    
    # Convert the output to a list of dictionaries
    exif_data = json.loads(exiftool_output)
    
    # Render the data in a table using Bootstrap
    table_rows = ""
    for item in exif_data[0].items():
        table_rows += f"<tr><td>{item[0]}</td><td>{item[1]}</td></tr>"
    table_html = f"<table class='table'>{table_rows}</table>"
    
    # Pass the table HTML and filename to the template
    return templates.TemplateResponse("index.html", {"request": request, "table_html": table_html, "filename": filename})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(api, host="127.0.0.1", port=8000)


