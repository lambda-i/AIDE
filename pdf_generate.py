from fpdf import FPDF
import json
import re  # Import regex module

class MedicalPDF(FPDF):
    def __init__(self, logo_path):
        super().__init__()
        self.logo_path = logo_path    

    def header(self):
        # Add a logo
        self.image(self.logo_path, 10, 8, 20)  # Adjust size and position of the logo
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 0, 0)  # Black text for the title
        self.cell(0, 10, 'Medical Conversation Summary', ln=True, align='C')
        self.ln(5)
        self.set_draw_color(0, 123, 255)  # Light blue for separator line
        self.line(10, 30, 200, 30)  # Separator line
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(0, 0, 0)  # Black text for footer
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(0, 123, 255)  # Light blue background for titles
        self.set_text_color(255, 255, 255)  # White text for titles
        self.cell(0, 10, title, ln=True, fill=True)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('Arial', '', 12)
        self.set_text_color(0, 0, 0)  # Black text for body
        self.multi_cell(0, 10, text)
        self.ln(5)

def extract_text_in_quotes(content):
    """Extract text within single or double quotes from a string."""
    match = re.search(r'["\']([^"\']+)["\']', content)
    return match.group(1) if match else content

def create_medical_pdf(json_data, logo_path, file_name="conversation_summary_medical.pdf"):
    pdf = MedicalPDF(logo_path)
    pdf.add_page()
    
    # Extract summary and full conversation from JSON
    summary = json_data.get("summary", "No summary provided.")
    full_conversation = json_data.get("full_conversation", [])

    # Add summary as a separate section
    pdf.chapter_title("Summary")
    pdf.chapter_body(summary)

    # Add full conversation with nice formatting
    pdf.chapter_title("Full Conversation")
    for msg in full_conversation:
        role = "User" if msg["role"] == "user" else "Assistant"
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 0, 0)  # Black text for role
        pdf.cell(0, 10, f"{role}:", ln=True)
        
        # Extract text in quotes for user role
        content = extract_text_in_quotes(msg["content"]) if msg["role"] == "user" else msg["content"]
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, content)
        pdf.ln(2)
    
    # Save the PDF
    pdf.output(file_name)
    return file_name

logo_path = "./lambdai.png"  # Replace with your actual logo file path

with open('./test.json', 'r') as json_file:
    json_data = json.load(json_file)  # Parse the JSON file into a Python dictionary

file_path = create_medical_pdf(json_data, logo_path)
print(f"Formatted PDF saved at: {file_path}")