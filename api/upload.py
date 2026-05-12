import os
import secrets
import logging
from typing import List, Tuple

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse

router = APIRouter()

logger = logging.getLogger(__name__)


def create_session_directory(session_id: str) -> Tuple[str, str]:
    """Build (and create) the upload dir for this session under <app_root>/uploaded_files/."""
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    upload_dir = os.path.join(parent_dir, "uploaded_files", session_id)

    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)

    return upload_dir, current_dir


class change_directory:
    """Context manager kept for parity with the previous module — safe to use elsewhere."""
    def __init__(self, path):
        self.path = path
        self.original_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_path)


@router.post('/api/upload')
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(..., max_size=100_000_000),
):
    # Pull the session ID from the cookie. If the cookie isn't there — which
    # is what's been happening on Azure — mint one ourselves and set it on
    # the response so the follow-up /api/getallmeta call lands in the same dir.
    session_id = request.cookies.get('session_id')
    minted_new = False
    if not session_id:
        session_id = secrets.token_hex(16)
        minted_new = True
        logger.warning(
            "No session_id cookie on /api/upload; minted a fresh one (%s). "
            "Session middleware may not be setting the cookie correctly.",
            session_id,
        )
    else:
        logger.debug("session_id from cookie: %s", session_id)

    upload_dir, _ = create_session_directory(session_id)
    logger.debug("Writing %d file(s) to %s", len(files), upload_dir)

    saved = []
    failed = []
    for file in files:
        try:
            contents = await file.read()
            target = os.path.join(upload_dir, file.filename)
            with open(target, "wb") as f:
                f.write(contents)
            saved.append(file.filename)
            logger.debug("Saved %s (%d bytes)", file.filename, len(contents))
        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})
            logger.exception("Failed to save %s", file.filename)

    response = JSONResponse(
        content={
            "ok": True,
            "session_id": session_id,
            "saved": saved,
            "failed": failed,
        },
        headers={"Cache-Control": "no-cache"},
    )

    # If we had to mint a session_id ourselves, set the cookie on this
    # response so the browser uses it on the next request. samesite=lax
    # is fine here since /api/upload and /api/getallmeta are same-origin.
    if minted_new:
        response.set_cookie(
            key='session_id',
            value=session_id,
            httponly=True,
            samesite='lax',
            max_age=3600,
            path='/',
        )

    return response