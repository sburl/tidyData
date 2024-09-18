import os
import re
from collections import defaultdict

def get_size(start_path='.'):
    """Returns the size of a file or folder in bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def human_readable_size(size_in_bytes):
    """Convert size in bytes to a human-readable format (e.g., GB, MB, KB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f}{unit}"
        size_in_bytes /= 1024

def get_symbol_for_depth(depth):
    """Returns the appropriate symbol for the given folder depth."""
    symbols = ['-', '*', '~', '=', '-']
    if depth < len(symbols):
        return symbols[depth]
    return symbols[-1]

def sanitize_folder_name(name):
    """
    Removes any alphanumeric string that looks like a UUID or hash from the folder name.
    This assumes UUID-like strings are 32 characters of alphanumeric text.
    """
    # Regex to match a UUID-like string (alphanumeric string of 32 or more characters)
    return re.sub(r'\b[a-f0-9]{32,}\b', '', name).strip()

def analyze_folder(folder_path, depth=0, file_type_summary=None, last_depth=0):
    """Analyzes the folder, its subfolders and files, and returns a formatted string of the analysis."""
    folder_summary = []
    total_size = get_size(folder_path)
    
    if total_size < 5 * 1024 * 1024:  # Skip folders smaller than 5MB
        return "", last_depth

    indent = ' ' * 4 * depth
    
    # Add extra line breaks when we go up a folder level
    if depth < last_depth:
        folder_summary.append("\n")

    # Sanitize folder name to remove any UUID or hash-like strings
    sanitized_folder_name = sanitize_folder_name(os.path.basename(folder_path))
    folder_summary.append(f"{indent}{get_symbol_for_depth(depth)} folder -> {sanitized_folder_name}: {human_readable_size(total_size)}")

    file_types = defaultdict(list)
    subfolders = []

    # Traverse the directory
    for dirpath, dirnames, filenames in os.walk(folder_path):
        # Handle files in current directory
        for file in filenames:
            file_size = os.path.getsize(os.path.join(dirpath, file))
            if file_size < 5 * 1024 * 1024:  # Skip files smaller than 5MB
                continue
            file_ext = os.path.splitext(file)[1]
            file_types[file_ext].append(file_size)
            
            # Update the global file type summary
            if file_type_summary is not None:
                file_type_summary[file_ext]['count'] += 1
                file_type_summary[file_ext]['size'] += file_size
        
        # Add subfolder names for recursive analysis
        for subfolder in dirnames:
            subfolder_path = os.path.join(dirpath, subfolder)
            if get_size(subfolder_path) >= 5 * 1024 * 1024:  # Skip subfolders smaller than 5MB
                subfolders.append(subfolder)
        
        # Only process the first level (do not recurse again in this loop)
        break

    # Add file type information on one line per type
    if file_types:
        for ext, sizes in file_types.items():
            count = len(sizes)
            total_size_ext = sum(sizes)
            folder_summary.append(f"{indent}{' ' * 4}{get_symbol_for_depth(depth + 1)} {count} x {ext} ({human_readable_size(total_size_ext)})")
    
    # Add subfolder information, just the folder names, and recursively analyze them
    if subfolders:
        for subfolder in subfolders:
            subfolder_path = os.path.join(folder_path, subfolder)
            subfolder_summary, last_depth = analyze_folder(subfolder_path, depth + 1, file_type_summary, depth)
            folder_summary.append(f"\n{subfolder_summary}")

    return "\n".join(folder_summary), depth

def export_to_txt(folder_path, content):
    """Exports the analysis to a .txt file in the original folder."""
    output_file = os.path.join(folder_path, "folder_analysis.txt")
    with open(output_file, 'w') as f:
        f.write(content)
    print(f"Analysis exported to {output_file}")

def generate_file_type_summary(file_type_summary):
    """Generates a summary of all file types encountered and their total sizes."""
    summary_lines = ["File Type Summary:\n"]
    for ext, data in file_type_summary.items():
        count = data['count']
        total_size = data['size']
        summary_lines.append(f"- {count} x {ext} ({human_readable_size(total_size)})")
    summary_lines.append("\n")  # Add an extra line break after the summary
    return "\n".join(summary_lines)

if __name__ == "__main__":
    # You can optionally provide the folder path here, or it will prompt for input if left blank
    folder_path = "/Users/sqb/Downloads/"  # <-- Change this to your default folder or leave blank

    if not folder_path or folder_path == "/Users/sqb/Downloads/":
        folder_path = input("Enter the path to the folder: ")

    # Dictionary to hold global file type summary (count and total size)
    file_type_summary = defaultdict(lambda: {'count': 0, 'size': 0})

    # Perform folder analysis
    analysis, _ = analyze_folder(folder_path, file_type_summary=file_type_summary)
    
    # Generate file type summary
    file_type_summary_output = generate_file_type_summary(file_type_summary)

    # Combine the summary and the detailed folder analysis
    final_output = file_type_summary_output + analysis

    if analysis:
        print(final_output)
        export_to_txt(folder_path, final_output)
    else:
        print(f"No files or folders larger than 5MB in '{folder_path}'.")