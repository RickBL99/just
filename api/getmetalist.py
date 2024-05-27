import os
import logging
import platform

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates/")


def setup_logger():
    logger_instance = logging.getLogger(__name__)
    logger_instance.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger_instance.addHandler(handler)
    return logger_instance


logger = setup_logger()


def get_upload_directory():
    if platform.system() == "Darwin":
        return os.path.join("uploaded_files")
    return os.path.join("/home/uploaded_files/")


def filter_image_files(directory):
    valid_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.gif', '.bmp', '.psd', '.raw', '.dng', '.cr2', '.nef', '.sr2'}
    return [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and os.path.splitext(f)[1].lower() in valid_extensions
    ]


@router.post('/api/getmetalist')
async def get_metadata(request: Request):
    logger.info("Request received for get_metadata endpoint")

    upload_dir = get_upload_directory()
    file_list = filter_image_files(upload_dir)

    if not file_list:
        return templates.TemplateResponse('no_files_found.html', context={'request': request}, status_code=200, media_type='text/html')

    return templates.TemplateResponse(
        'file_list_meta.html',
        context={'request': request, 'file_list': file_list, 'stripname': stripname}
    )
