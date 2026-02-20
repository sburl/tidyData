import os

def combine_text_files(folder_path, output_file="Combined_Text_Files.txt", extensions=None):
    """
    Combines all text files from a specified folder into a single file.
    
    Args:
        folder_path: Path to the folder containing text files
        output_file: Name of the output file (default: "Combined_Text_Files.txt")
        extensions: List of file extensions to include (e.g., ['.txt', '.md', '.py', '.js'])
                    If None, includes common text file extensions
    """
    # Default extensions if none provided
    if extensions is None:
        extensions = ['.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', 
                     '.json', '.xml', '.yaml', '.yml', '.csv', '.log', '.sh', '.bat', 
                     '.java', '.cpp', '.c', '.h', '.hpp', '.swift', '.go', '.rs', '.rb', 
                     '.php', '.sql', '.r', '.m', '.scala', '.kt', '.dart', '.lua', '.pl']
    
    # Normalize extensions to lowercase
    extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
    
    # Define the full path of the output file in the original folder
    output_file_path = os.path.join(folder_path, output_file)
    
    # Track files found and combined
    files_combined = []
    
    # Create/open the output file in write mode
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        # Loop through all files in the folder
        for filename in sorted(os.listdir(folder_path)):
            file_path = os.path.join(folder_path, filename)
            
            # Skip if it's a directory or the output file itself
            if os.path.isdir(file_path) or filename == output_file:
                continue
            
            # Check if file has one of the target extensions
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in extensions:
                try:
                    # Get file stats for metadata
                    file_stats = os.stat(file_path)
                    file_size = file_stats.st_size
                    
                    # Write a clear delimiter with the file name preserved prominently
                    outfile.write("\n" + "=" * 80 + "\n")
                    outfile.write(f"FILENAME: {filename}\n")
                    outfile.write(f"FILEPATH: {file_path}\n")
                    outfile.write(f"FILESIZE: {file_size} bytes\n")
                    outfile.write("=" * 80 + "\n\n")
                    
                    # Open each text file and append its contents
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()
                        outfile.write(content)
                        if not content.endswith('\n'):
                            outfile.write('\n')
                    
                    outfile.write("\n" + "=" * 80 + "\n")
                    outfile.write(f"END OF FILE: {filename}\n")
                    outfile.write("=" * 80 + "\n\n")
                    files_combined.append(filename)
                except Exception as e:
                    print(f"Warning: Could not read {filename}: {e}")
    
    if files_combined:
        print(f"Successfully combined {len(files_combined)} file(s):")
        for f in files_combined:
            print(f"  - {f}")
        print(f"\nCombined file saved to: {output_file_path}")
    else:
        print(f"No text files found in: {folder_path}")
        print(f"Looking for extensions: {', '.join(extensions)}")

# Example usage
if __name__ == "__main__":
    # Folder containing text files to combine
    folder_path = "/Users/sqb/Library/Mobile Documents/com~apple~CloudDocs/Downloads/autoSort/Grampy audio/processed/transcripts"
    
    # You can specify custom extensions if needed:
    # combine_text_files(folder_path, extensions=['.txt', '.md', '.py'])
    
    # Or use default extensions (includes most common text file types):
    combine_text_files(folder_path)
