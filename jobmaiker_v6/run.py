from backend.app import app
from backend.database import init_db

if __name__ == "__main__":
    print("Initializing Database tables and initial seeds...")
    init_db()
    print("Starting JobMaker Flask server on http://127.0.0.1:5000...")
    app.run(host="127.0.0.1", port=5000, debug=True)
