import os
import re
import requests
from flask import Flask, render_template, request, send_from_directory, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Directory to save downloaded media
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def sanitize_filename(filename):
    """Sanitize the filename to remove invalid characters."""
    return re.sub(r"[^\w\-_\. ]", "_", filename)

def download_media_file(media_url, filename):
    """Download the media file from the provided URL."""
    try:
        response = requests.get(media_url, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            return file_path
        else:
            print(f"Failed to download media. HTTP Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred while downloading the media: {e}")
        return None

def fetch_instagram_media(url):
    """Fetch the media URL (video or image) from an Instagram post."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(url)
            page.wait_for_timeout(5000)

            # Check for video or image element
            video_element = page.query_selector("video")
            image_element = page.query_selector("img")

            if video_element:
                media_url = video_element.get_attribute("src")
                media_type = "video/mp4"
            elif image_element:
                media_url = image_element.get_attribute("src")
                media_type = "image/jpeg"
            else:
                media_url = None
                media_type = None

            if media_url:
                # Use part of the Instagram post URL as a unique filename
                post_id = url.split("/")[-2]
                filename = sanitize_filename(f"Skpost_{post_id}.{media_type.split('/')[1]}")
                file_path = download_media_file(media_url, filename)  # Save media locally
                return media_url, filename, media_type, file_path
            return None, None, None, None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None, None, None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        instagram_url = request.json.get("instagram_url")
        if instagram_url:
            media_url, filename, media_type, file_path = fetch_instagram_media(instagram_url)
            if media_url:
                return jsonify({
                    "media_url": media_url,
                    "filename": filename, 
                     "media_type": media_type
                     })
        return jsonify({"error": "Unable to fetch media from the provided URL."})
    return render_template("index.html")

@app.route("/download/<filename>")
def download(filename):
    """Serve the downloaded file."""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    else:
        return "File not found.", 404

if __name__ == "__main__":
    app.run(debug=True)
