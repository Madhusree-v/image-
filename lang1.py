from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
DetectorFactory.seed = 0  # For consistent results
import pytesseract
from PIL import Image
import os
import io
import json
import fitz  # PyMuPDF
import pdfplumber
import csv
import pypdfium2 as pdfium
import matplotlib.pyplot as plt
from io import BytesIO

app = Flask(__name__, template_folder=r"C:\Users\DELL\Downloads\frjsonfl")

# Configuration
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'jfif', 'webp', 'bmp', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Convert PDF to images
def convert_pdf_to_images(file_path, scale=300/72):
    pdf_file = pdfium.PdfDocument(file_path)
    page_indices = [i for i in range(len(pdf_file))]

    renderer = pdf_file.render(
        pdfium.PdfBitmap.to_pil,
        page_indices=page_indices,
        scale=scale,
    )

    list_final_images = []

    for i, image in zip(page_indices, renderer):
        image_byte_array = BytesIO()
        image.save(image_byte_array, format='jpeg', optimize=True)
        image_byte_array = image_byte_array.getvalue()
        list_final_images.append(dict({i: image_byte_array}))

    return list_final_images

# Detect language from text
def detect_language(text):
    try:
        return detect(text)
    except LangDetectException as e:
        return f"Language detection error: {e}"

# Image text extraction
def extract_text_from_image(image_bytes):
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang='eng')  # Default to English
        lang = detect_language(text)
        return text, lang
    except Exception as e:
        return str(e), "unknown"

# PDF text extraction functions
def extract_text_pymupdf(pdf_path):
    text = ''
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        return f"Error extracting text with PyMuPDF: {e}", "unknown"
    return text, detect_language(text)

def extract_text_and_tables_pdfplumber(pdf_path):
    text = ''
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                
                page_tables = page.extract_tables()
                for table in page_tables:
                    tables.append(table)
    except Exception as e:
        return f"Error extracting text and tables with pdfplumber: {e}", [], "unknown"
    return text, tables, detect_language(text)

def save_tables_as_csv(tables, filename):
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for table in tables:
                for row in table:
                    writer.writerow(row)
                writer.writerow([])  # Add an empty line between tables
    except Exception as e:
        return f"Error saving tables to CSV: {e}"

def extract_text_from_pdf(pdf_path):
    text_pymupdf, lang_pymupdf = extract_text_pymupdf(pdf_path)
    text_pdfplumber, tables, lang_pdfplumber = extract_text_and_tables_pdfplumber(pdf_path)
    combined_text = f"--- PyMuPDF Extraction ---\n{text_pymupdf.strip()}\n\n--- pdfplumber Extraction ---\n{text_pdfplumber.strip()}"
    
    if not combined_text.strip():
        combined_text = "No text extracted from the PDF."

    combined_language = lang_pymupdf if lang_pymupdf != "unknown" else lang_pdfplumber

    return combined_text, tables, combined_language

# Placeholder for LLM processing
def process_with_llm(text):
    # Integrate with LLM API or library here
    # For now, return the input text as is
    return text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        if filename.lower().endswith('.pdf'):
            # Convert PDF to images and extract text
            images = convert_pdf_to_images(file_path)
            combined_text = ""
            detected_languages = set()
            for image_dict in images:
                for page_num, image_bytes in image_dict.items():
                    text, lang = extract_text_from_image(image_bytes)
                    combined_text += f"--- Page {page_num + 1} ---\n{text}\n"
                    detected_languages.add(lang)
            
            csv_filename = os.path.splitext(filename)[0] + '_tables.csv'
            csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
            tables = []
            save_tables_as_csv(tables, csv_file_path)  # Currently not extracting tables from images

            return jsonify({
                'text': process_with_llm(combined_text),
                'csv': csv_filename,
                'languages': list(detected_languages)
            })
        else:
            # Process image file
            text, lang = extract_text_from_image(file_path)
            json_output = json.dumps({'text': text, 'language': lang}, indent=4)
            csv_output = 'text\n' + text.replace('\n', '\n')
            
            return jsonify({
                'text': text,
                'json': json_output,
                'csv': csv_output,
                'language': lang
            })
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(debug=True)
