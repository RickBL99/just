import os
import platform
import secrets
import shutil
import subprocess
import time
import shlex
import logging
from typing import List, Tuple

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from PIL import Image

router = APIRouter()
templates = Jinja2Templates(directory="templates/")

# Create logger object
logger = logging.getLogger(__name__)

# Set logger level
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add formatter to console handler
ch.setFormatter(formatter)

# Add console handler to logger
logger.addHandler(ch)

fh = logging.FileHandler('mylog.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


def configure_logging():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

    # Add a StreamHandler to log to console
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


configure_logging()


def create_session_directory(session_id: str) -> Tuple[str, str]:
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
    logger.debug(f"Session ID retrieved from request cookies: {session_id}")

    # Create a directory for the session_id
    upload_dir, _ = create_session_directory(session_id)
    logger.debug(f"Directory created for session ID {session_id} at {upload_dir}")

    logger.debug("Starting file upload")

    # Safely change directories using a context manager
    with change_directory(os.getcwd()):
        for file in files:
            contents = await file.read()
            time.sleep(1)  # Simulate processing delay
            logger.debug(f"Received file {file.filename}")
            with open(os.path.join(str(upload_dir), file.filename), "wb") as f:
                f.write(contents)

    logger.debug("File upload complete")

    return templates.TemplateResponse('upload.html', context={'request': request}, headers={'Cache-Control': 'no-cache'})


class change_directory:
    def __init__(self, path):
        self.path = path
        self.original_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_path)
