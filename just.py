from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import subprocess
import json
import os
import platform

app = FastAPI()
templates = Jinja2Templates(directory="templates")
current_dir = os.getcwd()


if platform.system() == "Darwin":
    # macOS go to this path.
    upload_dir = os.path.join(current_dir, "uploaded_files")
    static_dir = os.path.join(current_dir, "static")
    downloads_dir = os.path.join(current_dir, "downloads")
    print("ITS A MAC!")
else:
    # Ubuntu (or other Linux distros) go to this path.
    upload_dir = "uploaded_files"
    static_dir = "static"
    downloads_dir = "downloads"
    print("ITS NOT A MAC!")

# Mount the directories

print(upload_dir)
print()
print(static_dir)
print()
print(downloads_dir)


app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/uploaded_files", StaticFiles(directory=upload_dir), name="uploaded_files")




@app.get("/")
def form_post(request: Request):
    result = "Get Files To Upload"
    print(result)
    return templates.TemplateResponse('upload.html', context={'request': request, 'result': result})



@app.get("/result", response_class=HTMLResponse)
async def index(request: Request):
    filename = "test.jpg"
    
    # Run exiftool command to fetch all exif information
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
    uvicorn.run(app, host="127.0.0.1", port=8000)

