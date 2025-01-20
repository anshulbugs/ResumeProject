from flask import Flask, request, render_template, Response
import os
import csv
import requests
import io
import time
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_upload(filepath, directory):
    try:
        # Read the uploaded file
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            csv_reader = csv.reader(f)
            headers = next(csv_reader)  # Skip header

            # Convert to list to get total count
            rows = list(csv_reader)
            total_files = len(rows)

        yield f"data: Starting to process {total_files} files\n\n"

        # Ensure the output directory exists
        os.makedirs(directory, exist_ok=True)

        downloaded = 0
        failed = 0
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for idx, row in enumerate(rows, 1):
            if len(row) <= 8:
                yield f"data: ⚠️ Row {idx}: Not enough columns\n\n"
                failed += 1
                continue

            pdf_url = row[8].strip()
            if not pdf_url:
                yield f"data: ⚠️ Row {idx}: Empty PDF URL\n\n"
                failed += 1
                continue

            try:
                yield f"data: Downloading for {row[6].strip()}\n\n"
                response = requests.get(pdf_url, timeout=60)

                if response.status_code == 200:
                    filename = f"resume_{timestamp}_{idx}.pdf"
                    filepath = os.path.join(directory, filename)

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    downloaded += 1
                    yield f"data: ✅ Successfully downloaded: {filename}\n\n"
                else:
                    failed += 1
                    yield f"data: ❌ Failed to download (Status {response.status_code}): {pdf_url}\n\n"

            except Exception as e:
                failed += 1
                yield f"data: ❌ Error downloading {pdf_url}: {str(e)}\n\n"

            progress = (idx / total_files) * 100
            yield f"data: PROGRESS:{progress}\n\n"
            time.sleep(0.1)  # Prevent overwhelming the server

        summary = f"""📊 Download Summary:\n\n
Total Files: {total_files}\n
Successfully Downloaded: {downloaded}\n
Failed: {failed}\n
Download Directory: {directory}"""

        yield f"data: {summary}\n\n"
        yield "data: COMPLETE\n\n"

    except Exception as e:
        yield f"data: ❌ Fatal Error: {str(e)}\n\n"
        yield "data: COMPLETE\n\n"
    finally:
        # Clean up the temporary file
        if os.path.exists(filepath):
            os.remove(filepath)
            os.remove(UPLOAD_FOLDER)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        # Check if this is an SSE request
        if request.headers.get('accept') == 'text/event-stream':
            def stream():
                yield "data: Connected\n\n"
            return Response(stream(), mimetype='text/event-stream')
        return render_template('index.html')

    if request.method == 'POST':
        file = request.files.get('file')
        directory = request.form.get('directory', '')

        if not file or not directory:
            return Response("data: Error: Missing file or directory\n\n", mimetype='text/event-stream')

        # Save the file temporarily
        temp_filepath = os.path.join(UPLOAD_FOLDER, f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        file.save(temp_filepath)

        return Response(
            process_upload(temp_filepath, directory),
            mimetype='text/event-stream'
        )


if __name__ == '__main__':
    app.run(threaded=True)
