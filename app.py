from pathlib import Path

from flask import Flask, send_from_directory

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
APP_VERSION = "1.2.3"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
