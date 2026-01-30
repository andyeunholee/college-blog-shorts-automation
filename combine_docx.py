import os
from docx import Document

def getText(filename):
    doc = Document(filename)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

source_dir = r"h:\My Drive\Automation-H\AntiGravity\us_college_blog_shorts_automation\Blog_Style_References"
output_file = os.path.join(source_dir, "combined_style_references.txt")

all_text = ""

for filename in os.listdir(source_dir):
    if filename.endswith(".docx"):
        path = os.path.join(source_dir, filename)
        try:
            text = getText(path)
            all_text += f"\n\n--- FILE: {filename} ---\n\n"
            all_text += text
        except Exception as e:
            print(f"Error reading {filename}: {e}")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(all_text)

print(f"Combined text saved to {output_file}")
