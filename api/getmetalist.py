import os
import logging

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import platform

router = APIRouter()
templates = Jinja2Templates(directory="templates/")

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

@router.post('/api/getmetalist')
async def get_metadata(request: Request):

    logger.info("Request received for get_metadata endpoint")

    if platform.system() == "Darwin":
        # macOS go to this path.
        upload_dir = os.path.join("uploaded_files")
    else:
        # Ubuntu (or other Linux distros) go to this path.
        upload_dir = os.path.join("/home/uploaded_files/")

    # Get a list of all image files in the upload directory
    file_list = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.gif', '.bmp', '.psd', '.raw', '.dng', '.cr2', '.nef', '.sr2'))]

    if not file_list:
        return templates.TemplateResponse('no_files_found.html', context={'request': request}, status_code=200, media_type='text/html')
    else:
        # Pass the file list to the template
        return templates.TemplateResponse(
            'file_list_meta.html',
            context={'request': request, 'file_list': file_list, 'stripname': stripname})
