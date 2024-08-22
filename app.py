import os
import uuid
import zipfile
from flask import Flask, render_template, request, send_file, session
from flask_session import Session
from rembg import remove
from PIL import Image
from io import BytesIO
import base64
import logging
import datetime

app = Flask(__name__)
app.debug = True

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Configure session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'mysecret'
Session(app)

class BackgroundRemover:
    def __init__(self):
        self.image_data = []
        self.image_names = []
        self.zip_file = None

    def process_images(self, files):
        self.image_data = []  # Reset the list
        self.image_names = []  # Reset the list
        date_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        zip_filename = f'public/images_{date_str}.zip'
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for i, file in enumerate(files):
                    img = Image.open(file.stream)
                    result = remove(img)

                    # Convert image to RGBA to handle transparency
                    result = result.convert("RGBA")
                    width, height = result.size

                    # Define new size (4x6 inches at 300 DPI)
                    # Convert inches to pixels
                    new_width, new_height = 1200, 1800  # 4x6 inches at 300 DPI

                    # Calculate new size to maintain aspect ratio
                    aspect_ratio = width / height
                    target_aspect_ratio = new_width / new_height

                    if aspect_ratio > target_aspect_ratio:
                        # Wider than target aspect ratio
                        resize_width = new_width
                        resize_height = int(new_width / aspect_ratio)
                    else:
                        # Taller than target aspect ratio
                        resize_height = new_height
                        resize_width = int(new_height * aspect_ratio)

                    # Resize image to fit within target dimensions
                    resized_img = result.resize((resize_width, resize_height), Image.Resampling.LANCZOS)

                    # Create a new image with white background
                    new_img = Image.new("RGBA", (new_width, new_height), (255, 255, 255, 255))

                    # Calculate position to paste the resized image
                    x = (new_width - resize_width) // 2
                    y = (new_height - resize_height) // 2
                    new_img.paste(resized_img, (x, y), resized_img)

                    # Save image to ZIP file
                    img_io = BytesIO()
                    new_img.save(img_io, "PNG")
                    img_io.seek(0)

                    # Save image to ZIP file using original file name
                    zipf.writestr(f'{file.filename}', img_io.getvalue())

                    # Encode image to base64
                    image_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
                    self.image_data.append(image_base64)
                    self.image_names.append(file.filename)
        
            # Save the ZIP file name to session
            session['zip_file'] = zip_filename
            logging.info(f"ZIP file created: {zip_filename}")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            self.image_data = []
            self.image_names = []
            self.zip_file = None

    def get_image_data(self):
        return self.image_data

    def get_image_names(self):
        return self.image_names

@app.route("/", methods=["GET", "POST"])
def index():
    remover = BackgroundRemover()  # Đảm bảo sử dụng cùng một instance của BackgroundRemover
    if request.method == "POST":
        files = request.files.getlist("images")
        remover.process_images(files)

    image_data = remover.get_image_data()
    image_names = remover.get_image_names()
    zip_file = session.get('zip_file', None)

    # Combine image data and names into a list of tuples
    images_with_names = list(zip(image_data, image_names))

    return render_template("index.html", images_with_names=images_with_names, zip_file=zip_file)

@app.route('/download-zip')
def download_zip():
    zip_file = session.get('zip_file', None)
    print("ppppppp",zip_file)
    if zip_file and os.path.exists(zip_file):
        return send_file(zip_file, as_attachment=True)
    return "No ZIP file available", 404

if __name__ == "__main__":
    app.run()
