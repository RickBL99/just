import os
import platform
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


@router.post('/api/upload')
async def upload_files(request: Request, files: List[UploadFile] = File(..., max_size=100000000)):

    username = request.cookies.get("username")
    logging.debug(f'Upload request received from user {username}')

    current_dir = os.path.abspath(os.path.dirname(__file__))

    if platform.system() == "Darwin":
        # macOS go to this path.
        upload_dir = os.path.join(current_dir, "..", "uploaded_files")
        current_dir = os.getcwd()
        os.chdir(upload_dir)
        logging.debug("Operating system: macOS")
    else:
        # Ubuntu (or other Linux distros) go to this path.
        upload_dir = "/home/uploaded_files"
        current_dir = os.getcwd()
        os.chdir(upload_dir)
        logging.debug("Operating system: Linux")

    for file in files:

        file_ext = os.path.splitext(file.filename)[1].lower()

        logging.debug(f'File uploaded: {file.filename}')
        contents = await file.read()
        
        time.sleep(0.1)  # sleep for 100 milliseconds

        # Save original file
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            logging.debug(f"Writing file to {file_path}")
            f.write(contents)
        f.close()
        


    os.chdir(current_dir)
    
    return templates.TemplateResponse('index.html', context={'request': request})


