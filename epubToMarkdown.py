import os
import zipfile
import re


def epub_to_markdown(epub_path, output_path=None):
    """
    Converts a single EPUB file to Markdown.
    
    Args:
        epub_path: Path to the EPUB file
        output_path: Path for the output Markdown file (optional)
                     If None, uses the same name with .md extension
    
    Returns:
        Path to the created Markdown file, or None if conversion failed
    """
    try:
        markdown_content = []
        
        # EPUB is just a ZIP file
        with zipfile.ZipFile(epub_path, 'r') as zf:
            # Find all HTML/XHTML files
            html_files = [f for f in zf.namelist() 
                         if f.endswith(('.html', '.xhtml', '.htm'))]
            
            for html_file in sorted(html_files):
                html_content = zf.read(html_file).decode('utf-8', errors='ignore')
                
                # Convert HTML to Markdown
                markdown = html_to_markdown(html_content)
                
                if markdown.strip():
                    markdown_content.append(markdown.strip())
                    markdown_content.append("\n\n")
        
        # Combine all content
        final_content = '\n'.join(markdown_content)
        
        # Clean up excessive newlines
        while '\n\n\n' in final_content:
            final_content = final_content.replace('\n\n\n', '\n\n')
        
        # Determine output path
        if output_path is None:
            output_path = os.path.splitext(epub_path)[0] + '.md'
        
        # Write the Markdown file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        return output_path
        
    except Exception as e:
        print(f"Error converting {epub_path}: {e}")
        return None


def html_to_markdown(html):
    """
    Simple HTML to Markdown converter using regex.
    No external dependencies needed.
    """
    # Remove script and style blocks
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert headers
    html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<h5[^>]*>(.*?)</h5>', r'\n##### \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<h6[^>]*>(.*?)</h6>', r'\n###### \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert emphasis
    html = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert links
    html = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert paragraphs and line breaks
    html = re.sub(r'<p[^>]*>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</p>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<br[^>]*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<div[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</div>', '\n', html, flags=re.IGNORECASE)
    
    # Convert lists
    html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'</?[uo]l[^>]*>', '\n', html, flags=re.IGNORECASE)
    
    # Convert blockquotes
    html = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'\n> \1\n', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert code
    html = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n```\n\1\n```\n', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert horizontal rules
    html = re.sub(r'<hr[^>]*/?>', '\n---\n', html, flags=re.IGNORECASE)
    
    # Remove remaining HTML tags
    html = re.sub(r'<[^>]+>', '', html)
    
    # Decode common HTML entities
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = html.replace('&#39;', "'")
    html = html.replace('&rsquo;', "'")
    html = html.replace('&lsquo;', "'")
    html = html.replace('&rdquo;', '"')
    html = html.replace('&ldquo;', '"')
    html = html.replace('&mdash;', '—')
    html = html.replace('&ndash;', '–')
    html = html.replace('&hellip;', '…')
    
    # Clean up whitespace
    html = re.sub(r' +', ' ', html)
    html = re.sub(r'\n +', '\n', html)
    html = re.sub(r' +\n', '\n', html)
    
    return html.strip()


def convert_epub_folder(folder_path, output_folder=None):
    """
    Converts all EPUB files in a folder to Markdown files.
    
    Args:
        folder_path: Path to the folder containing EPUB files
        output_folder: Path to the output folder for Markdown files (optional)
                       If None, Markdown files are saved in the same folder as the EPUBs
    """
    # Validate input folder
    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found: {folder_path}")
        return
    
    # Create output folder if specified and doesn't exist
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    # Find all EPUB files
    epub_files = [f for f in os.listdir(folder_path) 
                  if f.lower().endswith('.epub') and not f.startswith('.')]
    
    if not epub_files:
        print(f"No EPUB files found in: {folder_path}")
        return
    
    print(f"Found {len(epub_files)} EPUB file(s) to convert\n")
    
    # Track conversion results
    successful = []
    failed = []
    
    # Process each EPUB file
    for filename in sorted(epub_files):
        epub_path = os.path.join(folder_path, filename)
        
        # Determine output path
        if output_folder:
            md_filename = os.path.splitext(filename)[0] + '.md'
            output_path = os.path.join(output_folder, md_filename)
        else:
            output_path = None  # Will use same folder as EPUB
        
        print(f"Converting: {filename}")
        
        result = epub_to_markdown(epub_path, output_path)
        
        if result:
            successful.append(filename)
            print(f"  ✓ Saved to: {result}")
        else:
            failed.append(filename)
            print(f"  ✗ Failed to convert")
    
    # Print summary
    print("\n" + "=" * 50)
    print("Conversion Summary")
    print("=" * 50)
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"  - {f}")


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Use command line argument as folder path
        folder_path = sys.argv[1]
        output_folder = sys.argv[2] if len(sys.argv) > 2 else None
        convert_epub_folder(folder_path, output_folder)
    else:
        # Default folder path
        folder_path = "/Users/sqb/Downloads/"
        convert_epub_folder(folder_path)
