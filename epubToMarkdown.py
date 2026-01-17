import os
from ebooklib import epub, ITEM_DOCUMENT
import html2text


def epub_to_markdown(epub_path, output_path=None):
    """
    Converts a single EPUB file to Markdown.
    
    Args:
        epub_path: Path to the EPUB file
        output_path: Path for the output Markdown file (optional)
    
    Returns:
        Path to the created Markdown file, or None if conversion failed
    """
    try:
        book = epub.read_epub(epub_path)
        
        # Configure html2text
        h = html2text.HTML2Text()
        h.body_width = 0  # No line wrapping
        h.ignore_images = False
        h.ignore_links = False
        
        # Get metadata
        title = book.get_metadata('DC', 'title')
        title = title[0][0] if title else os.path.splitext(os.path.basename(epub_path))[0]
        
        author = book.get_metadata('DC', 'creator')
        author = author[0][0] if author else None
        
        # Build markdown content
        parts = [f"# {title}\n"]
        if author:
            parts.append(f"**Author:** {author}\n")
        parts.append("\n---\n\n")
        
        # Convert each document in reading order
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            html = item.get_content().decode('utf-8', errors='ignore')
            markdown = h.handle(html)
            if markdown.strip():
                parts.append(markdown.strip() + "\n\n")
        
        content = ''.join(parts)
        
        # Clean up excessive newlines
        while '\n\n\n' in content:
            content = content.replace('\n\n\n', '\n\n')
        
        # Determine output path
        if output_path is None:
            output_path = os.path.splitext(epub_path)[0] + '.md'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
        
    except Exception as e:
        print(f"Error converting {epub_path}: {e}")
        return None


def convert_epub_folder(folder_path, output_folder=None):
    """
    Converts all EPUB files in a folder to Markdown files.
    
    Args:
        folder_path: Path to the folder containing EPUB files
        output_folder: Path to the output folder (optional, defaults to same folder)
    """
    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found: {folder_path}")
        return
    
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    epub_files = [f for f in os.listdir(folder_path) 
                  if f.lower().endswith('.epub') and not f.startswith('.')]
    
    if not epub_files:
        print(f"No EPUB files found in: {folder_path}")
        return
    
    print(f"Found {len(epub_files)} EPUB file(s) to convert\n")
    
    successful, failed = [], []
    
    for filename in sorted(epub_files):
        epub_path = os.path.join(folder_path, filename)
        
        if output_folder:
            md_filename = os.path.splitext(filename)[0] + '.md'
            output_path = os.path.join(output_folder, md_filename)
        else:
            output_path = None
        
        print(f"Converting: {filename}")
        result = epub_to_markdown(epub_path, output_path)
        
        if result:
            successful.append(filename)
            print(f"  ✓ Saved to: {result}")
        else:
            failed.append(filename)
            print(f"  ✗ Failed to convert")
    
    print("\n" + "=" * 50)
    print(f"Conversion Summary: {len(successful)} successful, {len(failed)} failed")
    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        output_folder = sys.argv[2] if len(sys.argv) > 2 else None
        convert_epub_folder(folder_path, output_folder)
    else:
        print("Usage: python epubToMarkdown.py <folder_path> [output_folder]")
