import os
import re
from collections import defaultdict


def get_size(start_path='.'):
    """Returns the size of a file or folder in bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp) and os.path.isfile(fp):
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

def analyze_folder(folder_path, depth=0, file_type_summary=None, last_depth=0, min_size=50 * 1024):
    """Analyzes the folder, its subfolders and files, and returns a formatted string of the analysis."""
    folder_summary = []
    total_size = get_size(folder_path)

    if total_size < min_size:
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
        dirnames[:] = sorted(d for d in dirnames if not os.path.islink(os.path.join(dirpath, d)))
        # Handle files in current directory
        for file in sorted(filenames):
            if os.path.islink(os.path.join(dirpath, file)):
                continue
            file_size = os.path.getsize(os.path.join(dirpath, file))
            if file_size < min_size:
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
            if get_size(subfolder_path) >= min_size:
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
            subfolder_summary, last_depth = analyze_folder(subfolder_path, depth + 1, file_type_summary, depth, min_size)
            folder_summary.append(f"\n{subfolder_summary}")

    return "\n".join(folder_summary), depth

def export_to_txt(folder_path, content, output_file=None):
    """Exports the analysis to a .txt file in the original folder."""
    output_file = output_file or os.path.join(folder_path, "folder_analysis.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Analysis exported to {output_file}")

def generate_file_type_summary(file_type_summary):
    """Generates a summary of all file types encountered and their total sizes, sorted by size."""
    # Sort file types by total size (descending order)
    sorted_file_types = sorted(file_type_summary.items(), key=lambda x: x[1]['size'], reverse=True)

    summary_lines = ["File Type Summary (Largest to Smallest):\n"]
    for ext, data in sorted_file_types:
        count = data['count']
        total_size = data['size']
        summary_lines.append(f"- {count} x {ext} ({human_readable_size(total_size)})")
    summary_lines.append("\n")  # Add an extra line break after the summary
    return "\n".join(summary_lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Report folder sizes and file types.')
    parser.add_argument('folder')
    parser.add_argument('--min-size', type=int, default=50 * 1024, help='Minimum size in bytes')
    parser.add_argument('-o', '--output')
    args = parser.parse_args()
    if args.min_size < 0 or not os.path.isdir(args.folder):
        parser.error('Provide an existing folder and nonnegative minimum size')
    summary = defaultdict(lambda: {'count': 0, 'size': 0})
    analysis, _ = analyze_folder(args.folder, file_type_summary=summary, min_size=args.min_size)
    report = generate_file_type_summary(summary) + analysis
    print(report)
    export_to_txt(args.folder, report, args.output)


if __name__ == '__main__':
    main()
