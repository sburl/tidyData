import os

def combine_markdown_files(folder_path, output_file="All Markdown.md"):
    # Define the full path of the output file in the original folder
    output_file_path = os.path.join(folder_path, output_file)

    # Create/open the output file in write mode
    with open(output_file_path, 'w') as outfile:
        # Loop through all files in the folder
        for filename in os.listdir(folder_path):
            if filename.endswith(".md"):
                file_path = os.path.join(folder_path, filename)
                
                # Write the largest header with the file name as the delimiter
                outfile.write(f"# {filename}\n\n")
                
                # Open each markdown file and append its contents to the output file
                with open(file_path, 'r') as infile:
                    outfile.write(infile.read())
                    outfile.write("\n\n")  # Add a new line after the content

    print(f"Combined markdown files saved to: {output_file_path}")

# Example usage
folder_path = "/Users/sqb/Downloads/"  # Replace with the path to your folder containing markdown files
combine_markdown_files(folder_path)