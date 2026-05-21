import os
import csv
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def parse_pdf_to_csv(pdf_path: str, provider: str = "gemini") -> str:
    """
    Parses a PDF into a CSV structure.
    Returns the filename of the newly generated CSV file.
    """
    prompt = """
    Extract all the firm/company data from this document and output it as a valid JSON array of objects.
    Each object in the array corresponds to a row in a CSV. 
    You MUST include at least the following two keys for every object:
    - "업체명" (Company Name - Required)
    - "소재지" (Location/Address - Required)
    
    You may also include other relevant information found in the document as additional keys, such as "업종", "배정인원", "연번", "관할청", etc.
    
    Only output the JSON array, without any markdown blocks (like ```json), just the raw JSON.
    """

    if provider == "openai":
        return _parse_with_openai(pdf_path, prompt)
    else:
        return _parse_with_gemini(pdf_path, prompt)


def _parse_with_gemini(pdf_path: str, prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in the environment variables.")
    
    genai.configure(api_key=api_key)

    print(f"Uploading {pdf_path} to Gemini...")
    sample_file = genai.upload_file(path=pdf_path, display_name=os.path.basename(pdf_path))
    print(f"Uploaded file '{sample_file.display_name}' as: {sample_file.uri}")

    # Wait for the file to be processed
    while sample_file.state.name == "PROCESSING":
        print("Waiting for file processing...")
        time.sleep(2)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        raise ValueError("PDF processing failed in Gemini.")

    # Using the recent flash lite model
    model = genai.GenerativeModel(model_name="gemini-3.1-flash-lite")
    
    print("Generating content with Gemini...")
    response = model.generate_content([sample_file, prompt])
    
    text = response.text.strip()
    
    # Clean up file from Gemini
    try:
        genai.delete_file(sample_file.name)
    except Exception as e:
        print("Could not delete file from Gemini:", e)
        
    return _process_json_to_csv(text, pdf_path)


def _parse_with_openai(pdf_path: str, prompt: str) -> str:
    import pdfplumber
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        
    client = OpenAI(api_key=api_key)
    
    print(f"Extracting text from {pdf_path} using pdfplumber...")
    text_content = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text_content += extracted + "\n"
                
    if not text_content.strip():
        raise ValueError("Could not extract any text from the PDF.")
        
    # To avoid exceeding context limits for very large PDFs, we might need to truncate, 
    # but gpt-5-mini has large context which is plenty for most PDFs.
    
    print("Generating content with OpenAI (gpt-5-mini)...")
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "You are a data extraction assistant."},
            {"role": "user", "content": f"{prompt}\n\nDocument Text:\n{text_content}"}
        ],
        temperature=0.1
    )
    
    text = response.choices[0].message.content.strip()
    
    return _process_json_to_csv(text, pdf_path)


def _process_json_to_csv(text: str, pdf_path: str) -> str:
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    data = json.loads(text.strip())
    
    output_filename = pdf_path.replace(".pdf", "_parsed.csv")
    if not data:
        raise ValueError("No data extracted.")
        
    # Gather all unique keys
    keys = []
    for row in data:
        for k in row.keys():
            if k not in keys:
                keys.append(k)
                
    # Ensure required columns are present and first
    if "업체명" not in keys:
        keys.insert(0, "업체명")
    else:
        keys.remove("업체명")
        keys.insert(0, "업체명")
        
    if "소재지" not in keys:
        keys.insert(1, "소재지")
    else:
        keys.remove("소재지")
        keys.insert(1, "소재지")
    
    with open(output_filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
        
    return os.path.basename(output_filename)
