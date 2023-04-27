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

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

# Function to create a folder for the session_id
def create_session_folder(session_id):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    if platform.system() == "Darwin":
        # macOS go to this path.
        upload_dir = os.path.join(current_dir, "..", "uploaded_files", session_id)
        current_dir = os.getcwd()
        os.chdir(upload_dir)
        print("Operating system: macOS")
        print(current_dir)
        print(upload_dir)
    else:
        # Ubuntu (or other Linux distros) go to this path.
        upload_dir = f"/just/uploaded_files/{session_id}"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        current_dir = os.getcwd()
        os.chdir(upload_dir)
        print("Operating system: Linux")
        print(current_dir)
        print(upload_dir)

    return upload_dir

@router.post('/api/upload')
async def upload_files(request: Request, files: List[UploadFile] = File(..., max_size=100000000)):
    # Generate a secure random session ID
    session_id = secrets.token_hex(16)
    
    # Set a cookie named "session_id" with the value of the session ID
    response.set_cookie(key="session_id", value=session_id)

    print("Added the cookie.")
    print(session_id)
    
    # Create a folder for the session_id
    upload_dir = create_session_folder(session_id)

    # divide files into batches of 5
    file_batches = [files[i:i+5] for i in range(0, len(files), 5)]

    for file_batch in file_batches:
        for file in file_batch:
            contents = await file.read()
            with open(os.path.join(upload_dir, file.filename), "wb") as f:
                f.write(contents)
        print(f"{len(file_batch)} file(s) uploaded successfully!")

    print("All files uploaded successfully!")

    print("NOW CHANGING TO CURRENT DIR")
    os.chdir(current_dir)
    
    return templates.TemplateResponse('index.html', context={'request': request})
