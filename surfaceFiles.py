import os
import shutil
import re

# Function to clean up folder names and file names, removing ASCII or location strings
def clean_name(name):
    # Remove long hash-like sequences (e.g., UUIDs, random ASCII strings) from names
    name = re.sub(r'[a-f0-9]{32,}', '', name)  # Remove any 32+ character hex strings
    name = re.sub(r'[^\w\s-]', '', name).strip()  # Remove any non-alphanumeric characters
    return name

# Function to truncate a filename to a maximum length
def truncate_filename(filename, max_length=255):
    if len(filename) > max_length:
        # If filename is too long, truncate it while keeping the extension intact
        name, ext = os.path.splitext(filename)
        truncated_name = name[:max_length - len(ext) - 3] + "..." + ext
        return truncated_name
    return filename

# Define file type categories
image_extensions = ['.jpeg', '.jpg', '.png', '.heic', '.tif', '.tiff', '.webp', '.gif', '.svg', '.avif']
pdf_extensions = ['.pdf']
spreadsheet_extensions = ['.xlsx', '.csv']
document_extensions = ['.docx', '.odt', '.pages', '.xml', '.asc', '.txt']

# Function to copy and move files based on their type
def process_files(src_folder):
    base_folder = os.path.dirname(src_folder)
    parent_folder = os.path.dirname(base_folder)  # One level higher than the source folder

    # Rename "Contents" folder to "{src_folder_name}_Content"
    folder_name = os.path.basename(src_folder)
    contents_folder = os.path.join(parent_folder, f"{folder_name}_Content")
    
    # Create the required folder structure
    folders = ['Inbox', 'Projects', 'Areas of Responsibility', 'Archive', 'Resources']
    for folder in folders:
        os.makedirs(os.path.join(contents_folder, folder), exist_ok=True)

    # Traverse the source folder
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            # Get the file extension
            file_extension = os.path.splitext(file)[1].lower()

            # Check if the file is in one of the target types
            if (file_extension in image_extensions + pdf_extensions + spreadsheet_extensions + document_extensions):
                # Create a non-destructive (deep) copy of the file
                file_path = os.path.join(root, file)
                
                # Find the relative path of the file to the src_folder
                relative_path = os.path.relpath(root, src_folder)

                # Split the relative path into folders
                path_parts = relative_path.split(os.sep)
                
                # The first part is the main folder, the second is the folder like "Inbox," etc.
                # We ignore these two and append the rest, if available
                if len(path_parts) > 2:
                    # Join the remaining parts to create the "appended path" using underscores
                    appended_path = "_".join(path_parts[2:])
                    file_name_without_ext, ext = os.path.splitext(file)  # Ensure the extension is preserved
                    new_filename = f"{appended_path} || {file_name_without_ext}{ext}"
                else:
                    # If no extra folders to append, just use the original filename
                    new_filename = file

                # Clean folder and file names to remove unwanted characters and hashes
                clean_name_parts = [clean_name(part) for part in path_parts[1:]]
                clean_file_name_without_ext = clean_name(os.path.splitext(file)[0])  # Clean the file name without extension
                
                # Append the cleaned path and file name with proper separators, ensuring the extension is intact
                if len(clean_name_parts) > 1:
                    clean_appended_path = "_".join(clean_name_parts[1:])
                    new_filename = f"{clean_appended_path} || {clean_file_name_without_ext}{file_extension}"
                else:
                    new_filename = f"{clean_file_name_without_ext}{file_extension}"

                # Determine destination based on subfolder
                clean_second_level_folder = clean_name(path_parts[1]) if len(path_parts) > 1 else ""
                if clean_second_level_folder in folders:
                    dest_folder = os.path.join(contents_folder, clean_second_level_folder)
                else:
                    dest_folder = contents_folder  # Default to Contents if subfolder doesn't match

                # Ensure the file name does not exceed the max file name length
                new_filename = truncate_filename(new_filename, 255)

                # Copy the file to the appropriate folder with the new name
                dest_path = os.path.join(dest_folder, new_filename)
                shutil.copy2(file_path, dest_path)

if __name__ == "__main__":
    # Specify the source folder path here
    source_folder = "/Users/sqb/Downloads/"
    process_files(source_folder)