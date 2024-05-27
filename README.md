
# Just The Meta!

A web application that allows users to upload images and fetch their metadata instantly. Created initially for internal use at https://superstock.com for our editing team, this application is running live at https://justthemeta.com on an Droplet (Ubuntu 22.1) at DigitalOcean.  Feel free to fork the repo and send PRs if you want to contribute.  Have fun with it. Please report anything goofy. Thanks - Rick Leckrone rick@superstock.com  

## Features

- **Image Upload**: Users can upload multiple images at once.
- **Metadata Retrieval**: The app uses `exiftool` to fetch and display detailed metadata for each uploaded image.
- **Responsive Design**: Whether on desktop or mobile, the user experience remains consistent and functional.
- **Logging**: Detailed logs ensure that any issues can be quickly identified and resolved.

## Getting Started

### Prerequisites

- Python 3.7 or later.
- FastAPI
- Other dependencies as listed in `requirements.txt`.

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/yourprojectname.git
   ```

2. Navigate to the project directory and install the dependencies:
   ```
   cd yourprojectname
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   uvicorn main:app --reload
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```

## Usage

1. **Upload Images**: Navigate to the 'Upload' page and select the images you wish to upload.
2. **View Metadata**: Once uploaded, click on the 'View Metadata' button to retrieve detailed metadata for each image.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please ensure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
