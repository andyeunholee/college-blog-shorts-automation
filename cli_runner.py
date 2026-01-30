import google.generativeai as genai
import os
from dotenv import load_dotenv
from duckduckgo_search import DDGS
import requests
import pypdf

# Load environment variables
load_dotenv()
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-3-pro-preview')
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    exit()

def download_cds(uni_name, url):
    try:
        dir_name = f"{uni_name}_Data"
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        file_path = os.path.join(dir_name, f"{uni_name}_CDS.pdf")
        print(f"Downloading CDS from {url}...")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
        return None
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages[:50]:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def search_university_info(uni_name):
    results = {}
    print(f"Searching web for {uni_name}...")
    with DDGS() as ddgs:
        # 1. Search CDS PDF Link (Robust Strategy)
        target_years = ["2025-2026", "2024-2025"]
        cds_results = []
        
        for year in target_years:
            queries = [
                f'"{uni_name}" Common Data Set {year} PDF filetype:pdf',
                f'site:.edu "{uni_name}" Common Data Set {year} PDF',
                f'"{uni_name}" CDS {year} PDF'
            ]
            
            for q in queries:
                print(f"Attempting search: {q}")
                try:
                    found = list(ddgs.text(q, max_results=1))
                    if found:
                        print(f"FAILED? No, FOUND! -> {found[0]['href']}")
                        cds_results = found
                        break 
                except Exception as e:
                    print(f"Search error: {e}")
            
            if cds_results:
                break
        
        cds_text_content = ""
        cds_file_path = None
        
        if cds_results:
            pdf_url = cds_results[0]['href']
            results['cds_url'] = pdf_url
            cds_file_path = download_cds(uni_name, pdf_url)
            if cds_file_path:
                print(f"Extracting text from {cds_file_path}...")
                cds_text_content = extract_text_from_pdf(cds_file_path)
                results['cds_status'] = f"Successfully downloaded and extracted: {cds_file_path}"
            else:
                results['cds_status'] = "Failed to download PDF."
        else:
            print("No CDS PDF found.")
            results['cds_status'] = "No CDS PDF found."

        results['cds_content'] = cds_text_content
        results['cds_path'] = cds_file_path

        print("Searching supplementary stats and essays...")
        stats_query = f"{uni_name} admission statistics class of 2029 2028 acceptance rate"
        results['stats'] = list(ddgs.text(stats_query, max_results=3))
        
        essay_query = f"{uni_name} supplemental essay prompts 2025-2026"
        results['essays'] = list(ddgs.text(essay_query, max_results=3))
        
    return results

def generate_blog_draft(uni_name, search_data, style_guide):
    cds_context = ""
    if search_data.get('cds_content'):
        cds_context = f"OFFICIAL CDS DATA (PRIMARY SOURCE):\n{search_data['cds_content'][:50000]}..." 
    
    prompt = f"""
    You are Andy Lee, a 10-year veteran college admission consultant.
    Write a blog post for {uni_name} targeting Korean parents.
    
    Data Source:
    {cds_context}
    
    Supplementary Web Search Data:
    {search_data.get('stats')}
    {search_data.get('essays')}
    
    Constraints (CRITICAL):
    1. STRICTLY prioritization: Use 'OFFICIAL CDS DATA' as the absolute source of truth. Only use 'Supplementary Web Search Data' if information is missing in the CDS.
    2. If a specific statistic is missing in the Data Source, DO NOT hallucinate or invent numbers. Instead, state "Data to be announced" or omit that specific metric.
    3. You may use your general knowledge for cultural context or advice, but quantitative data MUST come from the source.
    
    Style Guide (MUST FOLLOW):
    {style_guide}
    
    Output Format:
    Markdown. Ensure the title starts with "[{uni_name}]".
    Include the signature block exactly as defined in the style guide.
    """
    print("Sending prompt to Gemini...")
    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    university = "Harvard University"
    print(f"--- Starting CLI Process for {university} ---")
    
    # Load Style Guide
    try:
        with open("Persona_Style_Guide.md", "r", encoding="utf-8") as f:
            style_guide = f.read()
    except:
        print("Style Guide not found in current directory!")
        exit()

    # Search & Download
    search_data = search_university_info(university)
    
    # Generate
    draft = generate_blog_draft(university, search_data, style_guide)
    
    # Save
    output_filename = f"Draft_{university.replace(' ', '_')}.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(draft)
    
    print(f"--- Process Complete ---")
    print(f"Draft saved to: {output_filename}")
    if search_data.get('cds_path'):
        print(f"CDS PDF saved to: {search_data['cds_path']}")
