from fpdf import FPDF
import os

# Define paths
base_dir = r"h:\My Drive\Automation-H\AntiGravity\us_college_blog_shorts_automation\UCLA_Data"
txt_path = os.path.join(base_dir, "UCLA_Admission_News_2026.txt")
pdf_path = os.path.join(base_dir, "UCLA_Admission_News_2026.pdf")

# Create PDF
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)

# Read and write content
try:
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            # Replace characters not supported by standard font
            safe_line = line.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(200, 10, txt=safe_line, ln=True, align='L')
            
    pdf.output(pdf_path)
    print(f"Successfully created PDF: {pdf_path}")
except Exception as e:
    print(f"Error converting to PDF: {e}")
