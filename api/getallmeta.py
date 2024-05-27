import os
import json
import subprocess
import builtins
import logging
import time

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

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

router = APIRouter()
templates = Jinja2Templates(directory="templates/")

@router.post('/api/getallmeta')
async def getallmeta(request: Request, image_number: str = Query(None)):

    logger.debug("Waiting for 5 seconds before getting cookie.")
    time.sleep(5)
    logger.debug("Completed waiting for 5 seconds")

    logger.debug("getallmeta function called!")

    session_id = request.cookies.get("session_id")
    fullpath = os.path.join("uploaded_files", session_id)

    logger.debug("THE FULL PATH IS BELOW!!!")
    logger.debug(f"Full path: {fullpath}")
    logger.debug("THE FULL PATH IS ABOVE!!!")

    if not os.path.exists(fullpath):
        return templates.TemplateResponse('error.html', context={'request': request, 'error_message': "Please upload some images to get started."}, status_code=404, media_type='text/html')

    # Add a 5-second delay with logging
    logger.debug("Waiting for 5 seconds to ensure all files are available")
    time.sleep(5)
    logger.debug("Completed waiting for 5 seconds")

    all_metadata = []
    suffixes = [".jpg", ".jpeg", ".png", ".JPG", ".PNG", ".JPEG", ".gif", ".GIF", ".bmp", ".BMP", ".PSD", ".psd", ".RAW", ".raw", ".DNG", ".dng", ".CR2", ".cr2", ".NEF", ".nef", ".SR2", ".sr2"]

    for filename in os.listdir(fullpath):
        if any(filename.endswith(suffix) for suffix in suffixes):
            filepath = os.path.join(fullpath, filename)

            try:
                output = subprocess.check_output(['exiftool', '-j', filepath])
                data = json.loads(output)[0]
                pretty_metadata = json.dumps(data, indent=4)
                logger.debug(f"Metadata retrieved successfully for {filename}")

                # Get GPS data and add to the dictionary of results
                gps_data = {}
                if 'GPSLatitude' in data and 'GPSLongitude' in data:
                    gps_data['latitude'] = data['GPSLatitude']
                    gps_data['longitude'] = data['GPSLongitude']
                data['gps_data'] = gps_data

                all_metadata.append([filename, data])

            except subprocess.CalledProcessError as e:
                # Handle the exception and return a custom response if necessary
                error_code = e.returncode
                logger.debug(f"Error retrieving metadata for {filename}: {e.output.decode('utf-8')}, Error Code: {error_code}")
                return templates.TemplateResponse('error.html', context={'request': request, 'error_message': f"Error retrieving metadata for {filename}", 'error_code': error_code}, status_code=500, media_type='text/html')

    context = {"isinstance": builtins.isinstance}

    print(all_metadata)

    return templates.TemplateResponse('getallmeta.html', context={'request': request, 'all_metadata': all_metadata, 'context': context, 'fullpath': fullpath}, status_code=200, media_type='text/html')
