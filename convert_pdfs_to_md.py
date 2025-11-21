#!/usr/bin/env python3
"""
Script to convert PDF files to Markdown format.
"""

import os
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF (fitz) is not installed. Installing...")
    os.system(f"{sys.executable} -m pip install pymupdf")
    import fitz


def pdf_to_markdown(pdf_path, output_path=None):
    """
    Convert a PDF file to Markdown format.
    
    Args:
        pdf_path: Path to the input PDF file
        output_path: Path to the output Markdown file (optional)
    
    Returns:
        Path to the created Markdown file
    """
    if output_path is None:
        output_path = pdf_path.with_suffix('.md')
    
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    markdown_content = []
    markdown_content.append(f"# {pdf_path.stem}\n\n")
    
    # Extract text from each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        if text.strip():
            # Add page separator (except for first page)
            if page_num > 0:
                markdown_content.append(f"\n---\n\n## Page {page_num + 1}\n\n")
            else:
                markdown_content.append(f"## Page {page_num + 1}\n\n")
            
            # Clean up the text and format as markdown
            lines = text.split('\n')
            formatted_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    # Try to detect headings (lines that are short and in caps or have specific patterns)
                    if len(line) < 100 and line.isupper() and len(line) > 5:
                        formatted_lines.append(f"### {line}\n")
                    else:
                        formatted_lines.append(f"{line}\n")
            
            markdown_content.extend(formatted_lines)
            markdown_content.append("\n")
    
    doc.close()
    
    # Write to markdown file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(''.join(markdown_content))
    
    return output_path


def main():
    """Convert all PDFs in the Sample PDFs folder to Markdown."""
    script_dir = Path(__file__).parent
    pdf_dir = script_dir / "Sample PDFs"
    
    if not pdf_dir.exists():
        print(f"Error: Directory '{pdf_dir}' does not exist.")
        return
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in '{pdf_dir}'")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to convert...\n")
    
    for pdf_file in pdf_files:
        print(f"Converting: {pdf_file.name}")
        try:
            output_file = pdf_to_markdown(pdf_file)
            print(f"  ✓ Created: {output_file.name}\n")
        except Exception as e:
            print(f"  ✗ Error converting {pdf_file.name}: {str(e)}\n")
    
    print("Conversion complete!")


if __name__ == "__main__":
    main()

