import requests
import json
import base64
import markdown
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BLOG_FILE = "blog_draft.md"

def post_to_wordpress():
    # 1. Load Credentials from .env
    url_base = os.getenv("WP_URL")
    user = os.getenv("WP_USER")
    password = os.getenv("WP_APP_PASSWORD")

    if not url_base or not user or not password:
        print("Error: Missing credentials in .env file.")
        return

    url = f"{url_base}/wp-json/wp/v2/posts"
    
    # Encode credentials
    credentials = f"{user}:{password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }

    # ... (previous code) ...

    # 2. Read Blog Content
    try:
        with open(BLOG_FILE, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"Error: {BLOG_FILE} not found.")
        return

    # Extract Title
    lines = md_content.split('\n')
    title = "New Blog Post"
    body_md = []
    
    for line in lines:
        if line.strip().startswith('# ') and title == "New Blog Post":
            title = line.strip().replace('# ', '')
        else:
            body_md.append(line)
            
    body_content = '\n'.join(body_md)

    # Convert Markdown to HTML
    html_content = markdown.markdown(body_content)

    # 3. Handle Image Upload (if featured_image.png exists)
    image_id = None
    image_html = ""
    image_path = "featured_image.png"

    if os.path.exists(image_path):
        print(f"Uploading image: {image_path}...")
        media_url = f"{url_base}/wp-json/wp/v2/media"
        headers_img = {
            'Authorization': f'Basic {token}',
            'Content-Disposition': f'attachment; filename={image_path}',
            'Content-Type': 'image/png'
        }
        with open(image_path, 'rb') as img:
            data = img.read()
            
        res_img = requests.post(media_url, headers=headers_img, data=data)
        
        if res_img.status_code == 201:
            image_data = res_img.json()
            image_id = image_data['id']
            img_src = image_data['source_url']
            print(f"Image uploaded successfully. ID: {image_id}")
            
            # Create Image HTML to insert under title
            image_html = f'<figure class="wp-block-image"><img src="{img_src}" alt="{title} Campus Image"/></figure><br><br>'
        else:
            print(f"Image upload failed: {res_img.text}")

    # Prepend image to content
    final_content = image_html + html_content

    # 4. Create Post Data
    post = {
        'title': title,
        'content': final_content,
        'status': 'draft',
        'featured_media': image_id  # Set as featured image too
    }

    # 5. Send Request
    response = requests.post(url, headers=headers, json=post)
    # ... (rest of code) ...

    if response.status_code == 201:
        print(f"Success! Post created. ID: {response.json()['id']}")
        print(f"Link: {response.json()['link']}")
    else:
        print(f"Failed. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    post_to_wordpress()
