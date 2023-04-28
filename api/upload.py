import os
import platform
import secrets
import shutil
from typing import List
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from PIL import Image
import subprocess
import time
import shlex
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates/")

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

# Add a StreamHandler to log to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# Function to create a folder for the session_id
def create_session_folder(session_id):

    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    upload_dir = os.path.join(str(parent_dir), "uploaded_files", session_id)

    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    return upload_dir, current_dir


@router.post('/api/upload')
async def upload_files(request: Request, files: List[UploadFile] = File(..., max_size=100000000)): 

    # Get the session ID from the request cookies
    session_id = request.cookies.get('session_id')

    logging.info(f"Session ID retrieved from request cookies: {session_id}")

    # Create a folder for the session_id
    upload_dir, current_dir = create_session_folder(session_id)

    logging.info(f"Folder created for session ID {session_id} at {upload_dir}")

    # Divide into batches, bitches.
    logging.info("Starting file upload")

    this_dir = (os.getcwd())

    for file in files:
        contents = await file.read()
        logging.info(f"Received file {file.filename}")
        with open(os.path.join(str(upload_dir), file.filename), "wb") as f:
            f.write(contents)

    logging.info("File upload complete")
    os.chdir(this_dir)
    logging.info(f"Changed directory back to {this_dir}")

    return templates.TemplateResponse('upload.html', context={'request': request}, headers={'Cache-Control': 'no-cache'})
