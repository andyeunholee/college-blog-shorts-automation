import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from duckduckgo_search import DDGS
import requests
import base64
import markdown
import pypdf


# Load environment variables
load_dotenv()

# Configure Gemini
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-3-pro-preview')
except Exception as e:
    st.error(f"Error configuring Gemini: {e}")

# Page Config
st.set_page_config(page_title="College Blog Automation", page_icon="🎓", layout="wide")

st.title("🎓 Andy Lee's Admission Blog Generator")
st.markdown("Enter a university name to research, draft, and publish.")

# Inputs
university = st.text_input("University Name", placeholder="e.g., Harvard University")

# Helper: Download CDS PDF
def download_cds(uni_name, url):
    try:
        # Create Data Directory
        dir_name = f"{uni_name}_Data"
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        
        # Define File Path
        file_path = os.path.join(dir_name, f"{uni_name}_CDS.pdf")
        
        # Download
        # User-Agent header is important for some pdf sites
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
        return None
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None

# Helper: Extract Text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            # Limit to first 50 pages to avoid overload, usually enough for CDS
            for page in reader.pages[:50]:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

# Helper: Extract Text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            # Limit to first 50 pages to avoid overload, usually enough for CDS
            for page in reader.pages[:50]:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

# Search Function
def search_university_info(uni_name):
    results = {}
    with DDGS() as ddgs:
        # 1. Search CDS PDF Link (Robust Strategy)
        # Years to check: Current -> Previous
        target_years = ["2025-2026", "2024-2025"]
        
        # Query Templates (3-Step Net)
        # 1. Standard: "Harvard University" Common Data Set 2024-2025 PDF filetype:pdf
        # 2. Domain: site:.edu "Harvard University" Common Data Set 2024-2025
        # 3. Abbrev: "Harvard University" CDS 2024-2025 PDF
        
        cds_results = []
        
        for year in target_years:
            queries = [
                f'"{uni_name}" Common Data Set {year} PDF filetype:pdf',
                f'site:.edu "{uni_name}" Common Data Set {year} PDF',
                f'"{uni_name}" CDS {year} PDF'
            ]
            
            for q in queries:
                try:
                    # random sleep to avoid aggressive rate limiting if needed, but DDGS handles some.
                    found = list(ddgs.text(q, max_results=1))
                    if found:
                        cds_results = found
                        # found a match, break inner loop (queries)
                        break 
                except Exception as e:
                    print(f"Search error for {q}: {e}")
                    continue
            
            if cds_results:
                # found a match, break outer loop (years)
                break
        
        cds_text_content = ""
        cds_file_path = None
        
        if cds_results:
            pdf_url = cds_results[0]['href']
            results['cds_url'] = pdf_url
            
            # Download and Extract
            cds_file_path = download_cds(uni_name, pdf_url)
            if cds_file_path:
                cds_text_content = extract_text_from_pdf(cds_file_path)
                results['cds_status'] = f"Successfully downloaded and extracted: {cds_file_path}"
            else:
                results['cds_status'] = "Failed to download PDF."
        else:
            results['cds_status'] = "No CDS PDF found."

        results['cds_content'] = cds_text_content
        results['cds_path'] = cds_file_path

        # 2. Search Admission Stats (Backup/Supplementary)
        # Search Admission Stats
        stats_query = f"{uni_name} admission statistics class of 2029 2028 acceptance rate"
        results['stats'] = list(ddgs.text(stats_query, max_results=3))
        
        # Search Essays
        essay_query = f"{uni_name} supplemental essay prompts 2025-2026"
        results['essays'] = list(ddgs.text(essay_query, max_results=3))
        
    return results

# Draft Function
def generate_blog_draft(uni_name, search_data, style_guide):
    
    # Prepare Data Context
    cds_context = ""
    if search_data.get('cds_content'):
        cds_context = f"OFFICIAL CDS DATA (PRIMARY SOURCE):\n{search_data['cds_content'][:50000]}..." # Limit char count for safety
    
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
    response = model.generate_content(prompt)
    return response.text

# WordPress Post Function
def publish_to_wordpress(title, content_html):
    url_base = os.getenv("WP_URL")
    user = os.getenv("WP_USER")
    password = os.getenv("WP_APP_PASSWORD")
    
    if not url_base or not user or not password:
        return False, "Missing .env credentials"

    url = f"{url_base}/wp-json/wp/v2/posts"
    credentials = f"{user}:{password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }
    
    post = {
        'title': title,
        'content': content_html,
        'status': 'draft' # Draft for safety
    }
    
    response = requests.post(url, headers=headers, json=post)
    if response.status_code == 201:
        return True, response.json()['link']
    else:
        return False, response.text

# --- Content Repurposing Functions ---

def generate_shorts_script(blog_content):
    prompt = f"""
    Based on the following blog post, create a 50-second YouTube Shorts script following the specific guidelines below.
    
    [Blog Content]
    {blog_content}
    
    [Guidelines & Persona]
    Content production utilizes Vrew software with specific technical specifications: 9:16 aspect ratio for shorts.
    Andy's work centers on bridging the information gap between Korean families and US higher education systems.
    
    Requirement:
    - Length: 50 seconds (approx 150 words).
    - Tone: Neutral, Fact-based, Clear delivery for AI Voice.
    - Format: NO emojis, NO scene descriptions. ONLY the spoken text.
    - Start with a Hook (Listen to the example).
    - End with the specific closing: "지금까지, SAT 부터 재정보조, 그리고, Transfer 가 필요없는, AP 와 대학수업까지 수강할수있는 엘리트 학원에서 알려 드렸습니다."
    - Output must be suitable for a single Excel cell (avoid excessive line breaks, just clean text intervals).
    
    [Example Style]
    요즘 대학들이 SAT 점수를 제출하지 않아도 된다고 하죠.
    하지만, 정말로 제출하지 않아도 괜찮을까요?
    꼭 그렇지는 않습니다.
    하버드, MIT, 듀크 같은 상위권 대학들의 최근 데이터를 보면
    합격생의 80~90%가 SAT 점수를 제출했습니다.
    왜일까요?
    첫째, SAT는 전국 공통 기준 시험이기 때문에
    학교마다 기준이 다른 내신 성적을 보완해 줍니다.
    둘째, 특히 STEM 계열이나 아시안 학생의 경우
    SAT 수학 점수가 강력한 경쟁력이 됩니다.
    결론은 이렇습니다.
    SAT는 더 이상 필수는 아니지만,
    여전히 합격을 좌우하는 전략적 선택입니다.
    점수를 제출하지 않아도 되지만,
    제출하지 않는 것이 오히려 불리할 수 있다는 점을 기억하세요.
    
    Create the script now.
    """
    response = model.generate_content(prompt)
    return response.text

def generate_shorts_title(script):
    prompt = f"""
    위 쇼츠 대본에 잘 어울리도록 쇼츠 영상을 위한 제목만 만들어 한국어로 출력해줘!
    실시간 검색 이슈등을 고려하여 눈에 확 띄도록! 후킹 문구 위주로 약간은 자극적으로 만들어 제목만 딱 출력해줘.
    
    [Shorts Script]
    {script}
    """
    response = model.generate_content(prompt)
    return response.text

def generate_shorts_description(script):
    prompt = f"""
    위 쇼츠대본에 잘 어울리도록 쇼츠 영상을 위한 유튜브 쇼츠 본문글을 만들어 한국어로 출력해줘! 
    검색 키워드 등도 포함하고 이모티콘도 적절히 포함해줘, 그이외 다른말 없이 본문글만 딱 출력해줘.
    
    [Shorts Script]
    {script}
    """
    response = model.generate_content(prompt)
    return response.text

def format_for_excel(text):
    prompt = f"""
    위의 글을 엑셀의 셀 하나에 들어갈수있도록 다시 써줘.
    (Remove multiple newlines, ensure it pastes as one block).
    
    [Text]
    {text}
    """
    response = model.generate_content(prompt)
    return response.text

def translate_to_english_natural(text):
    prompt = f"""
    위의 쇼츠영상의 한국어 본문글을 영어원어민이 번역한것 처럼 자연스럽게 영어로 다시 써줘.
    
    [Korean Text]
    {text}
    """
    response = model.generate_content(prompt)
    return response.text

def generate_longform_script(blog_content):
    prompt = f"""
    너는 30년차 작가이다. 위의 글로 롱폼 유튜브 영상을 만들려고해. 
    가능한 위의 블로그글의 모든 내용을 포함한 스크립을 정중하고 전문가 스타일로 해주고, 
    한글로 한사람이 읽을수있도록 모두 서술형으로 써주고, 
    단, 서론, 본론, 마무리와 같이 문단을 나눌때마다 글의 제목을 첨가해줘. 
    
    [Format Requirement - CRITICAL]
    - Output in **PLAIN TEXT** only.
    - Do NOT use Markdown symbols (like #, ##, **, -). 
    - For Headers, just use Brackets [Header] or simple text separation.
    - Ensure it is ready to copy and paste directly into Microsoft Word.
    
    모든 문장이 끝날때, ‘,’ 를 넣주고, 문장이 끝날때마다, 가능하면 “되겠습니다", "것입니다", “하겠습니다” 등의 끝맺음으로 대사를 써줘. 
    스크립은 10,000자 이내로 해줘 Think Hard. 
    유튜브 설명란에 time line 을 넣을수있도록 소제목으로 나눠주고, time line 도 밑에 같이 써줘.
    
    [Blog Content]
    {blog_content}
    """
    response = model.generate_content(prompt)
    return response.text

# Logic Flow
if st.button("🚀 Start Mission"):
    if not university:
        st.warning("Please enter a university name.")
    else:
        with st.status("Processing Mission...", expanded=True) as status:
            # 1. Load Persona
            st.write("📖 Loading Persona Style Guide...")
            try:
                with open("Persona_Style_Guide.md", "r", encoding="utf-8") as f:
                    style_guide = f.read()
            except:
                st.error("Style Guide not found!")
                st.stop()

            # 2. Search & Download CDS (Back to DuckDuckGo)
            st.write(f"🔍 Searching & Downloading CDS for {university}...")
            search_data = search_university_info(university)
            
            if search_data.get('cds_path'):
                st.success(f"✅ CDS PDF Downloaded: {search_data['cds_path']}")
            else:
                st.warning("⚠️ CDS PDF not found (using Web Snippets).")
                
            st.json({k:v for k,v in search_data.items() if k != 'cds_content'}, expanded=False)

            # 3. Draft
            st.write("✍️ Writing blog post with Gemini (Analysis of CDS Data)...")
            draft_content = generate_blog_draft(university, search_data, style_guide)
            st.session_state['draft_content'] = draft_content
            
            status.update(label="Mission Accomplished! Review the draft below.", state="complete")

if 'draft_content' in st.session_state:
    st.subheader("📝 Blog Draft Review")
    st.markdown(st.session_state['draft_content'])
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Publish to WordPress"):
            # Extract title
            lines = st.session_state['draft_content'].split('\n')
            title = lines[0].replace('#', '').strip() if lines else f"Blog: {university}"
            body_html = markdown.markdown(st.session_state['draft_content'])
            
            success, result = publish_to_wordpress(title, body_html)
            if success:
                st.success(f"Published successfully! [View Post]({result})")
            else:
                st.error(f"Failed to publish: {result}")
    
    st.markdown("---")
    st.subheader("🎬 Content Repurposing (Shorts & Video)")
    
    # 1. Shorts Script
    if st.button("Generate Shorts Script"):
        script = generate_shorts_script(st.session_state['draft_content'])
        st.session_state['shorts_script'] = script
    
    if 'shorts_script' in st.session_state:
        st.text_area("Shorts Script", st.session_state['shorts_script'], height=200)
        
        # 2. Title
        if st.button("Start Title Creation?"):
            title = generate_shorts_title(st.session_state['shorts_script'])
            st.session_state['shorts_title'] = title
        
        if 'shorts_title' in st.session_state:
            st.info(f"Title: {st.session_state['shorts_title']}")
            
            # 3. Description
            if st.button("Generate Description?"):
                desc = generate_shorts_description(st.session_state['shorts_script'])
                st.session_state['shorts_desc'] = desc
            
            if 'shorts_desc' in st.session_state:
                st.text_area("Description (Korean)", st.session_state['shorts_desc'])
                
                # 4. Excel Format (Korean)
                if st.button("Format for Excel (KR)?"):
                    excel_kr = format_for_excel(st.session_state['shorts_desc'])
                    st.code(excel_kr, language='text')

                # 5. Longform Script (Plain Text)
                if st.button("Generate Long-form Script?"):
                    with st.spinner("Writing long-form script (Plain Text)..."):
                        long_script = generate_longform_script(st.session_state['draft_content'])
                        st.session_state['long_script'] = long_script
                
                if 'long_script' in st.session_state:
                    st.subheader("📺 Long-form Script")
                    st.text_area("Long-form Script (Copy for Word)", st.session_state['long_script'], height=600)
                    # st.markdown removed to show plain text only
