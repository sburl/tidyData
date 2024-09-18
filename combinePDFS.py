import os
from PyPDF2 import PdfReader, PdfWriter

def combine_pdfs(folder_path, output_filename):
    # Get a list of all the PDF files in the folder
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
    pdf_files.sort()  # Optional: to ensure the order of merging

    # Create a PdfWriter object
    writer = PdfWriter()

    # Keep track of the total size of input PDFs
    total_input_size = 0

    for pdf_file in pdf_files:
        file_path = os.path.join(folder_path, pdf_file)
        total_input_size += os.path.getsize(file_path)  # Track the size of each input PDF

        # Open each PDF and append its pages to the writer
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page_num in range(len(reader.pages)):
                writer.add_page(reader.pages[page_num])

    # Save the combined PDF to the specified output file
    output_path = os.path.join(folder_path, output_filename)
    with open(output_path, 'wb') as output_pdf:
        writer.write(output_pdf)

    # Check if the new PDF size is less than or equal to the sum of input file sizes
    combined_pdf_size = os.path.getsize(output_path)

    if combined_pdf_size <= total_input_size:
        print(f"PDFs combined successfully into {output_filename}.")
    else:
        print("Warning: The combined PDF is larger than the sum of the input files.")

# Example usage
folder_path = '/Users/sqb/Documents/Developer/Other/Tegus4of4'  # Replace with your folder path
output_filename = 'Tegus4of4.pdf'  # Replace with desired output file name
combine_pdfs(folder_path, output_filename)