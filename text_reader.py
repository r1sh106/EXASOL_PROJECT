#install these packages
#pip install google-genai pydantic pillow

import os
import sqlite3
from pathlib import Path
from PIL import Image
from pydantic import BaseModel
from google import genai
from google.genai import types

# 1. Define the desired database schema / output structure
class ExtractedTextRecord(BaseModel):
    title_or_heading: str
    full_text: str
    detected_language: str
    tags: list[str]

# 2. Database setup helper
def init_db(db_path: str = "extracted_data.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            title TEXT,
            full_text TEXT,
            language TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# 3. Main helper function
def process_and_store_image(image_path: str, db_path: str = "extracted_data.db") -> bool:
    """
    Extracts text from an image using Gemini and stores the result in a SQLite database.
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    # Initialize the GenAI client (picks up GEMINI_API_KEY automatically)
    client = genai.Client(api_key="AQ.Ab8RN6Ic-qYlijSzF5lEIJ6y82N6OsrHqtOEpTx2BnrVfC8H6g")

    # Load image using PIL
    image = Image.open(image_path)

    # Call Gemini requesting structured JSON output matching the Pydantic schema
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            image,
            "Extract all readable text from this image. Provide a clear title or heading, the full extracted text, the detected language, and key tags representing the content."
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedTextRecord,
        ),
    )

    # Parse the structured response into the Pydantic object
    record = ExtractedTextRecord.model_validate_json(response.text)

    # Save extracted record to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO image_texts (file_name, title, full_text, language, tags)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            Path(image_path).name,
            record.title_or_heading,
            record.full_text,
            record.detected_language,
            ", ".join(record.tags),  # Store tags as a comma-separated string
        ),
    )
    conn.commit()
    conn.close()

    return True

# Example Usage
if __name__ == "__main__":
    init_db()
    
    # Process an image
    sample_image = "receipt_or_document.jpg"
    if Path(sample_image).exists():
        process_and_store_image(sample_image)
        print(f"Successfully extracted and saved text from {sample_image}")

