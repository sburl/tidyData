# tidyData

**tidyData** is a collection of Python scripts designed to streamline data and file management tasks. This repository contains multiple programs, each with a specific function, making it easier to handle Markdown files, PDF documents, folder organization, and more.

## Programs Overview

### 1. combineMarkdown.py
This script combines all Markdown (`.md`) files from a specified folder into a single Markdown file. Each original file is separated by its name as a header, making it easy to navigate through the combined content.

I use this to combine Markdown files I export from Perplexity via the "Save My Chatbot" (Chrome extension)[https://chromewebstore.google.com/detail/save-my-chatbot-ai-conver/agklnagmfeooogcppjccdnoallkhgkod?hl=en].

**Usage:**
- Specify the folder containing Markdown files.
- Run the script to generate a combined Markdown file named `All Markdown.md`.

### 2. combinePDFS.py
This script merges all PDF files from a specified folder into a single output PDF. It ensures that the resulting document contains all pages from the individual PDFs in the desired order.

I use this to combine PDF files since Preview on Mac is actually awful (adding 5 x 10mb PDFs together makes a 200mb file).

**Usage:**
- Specify the folder containing PDF files.
- Run the script to generate a combined PDF file.

### 3. docSplice.py
This script processes document files, extracting specific sections based on predefined patterns and saving them into new files. It is useful for splitting or reorganizing content from larger documents.

I use this to split up 1,000 page word docs so I can feed them to LLMs.

**Usage:**
- Specify the folder containing the documents to be processed.
- Define the patterns for content extraction.
- Run the script to create new files with extracted content.

### 4. folderSizer.py
This script analyzes the size of folders and provides detailed information about space usage, including the composition of files within a folder. It is helpful for identifying large files and understanding storage utilization.

I used this with an export of my entire Notion database to pull out all of the photos so I could process them with an LLM.

**Usage:**
- Specify the folder to be analyzed.
- Run the script to get an overview of folder sizes and file composition.

### 5. surfaceFiles.py
This script traverses a specified folder and copies certain files into a newly created folder structure. The new structure is organized based on the original file location, with cleaned and formatted filenames.

I used this to flatten the photos from my aforementioned Notion database export.

**Usage:**
- Specify the source folder to be processed.
- Run the script to create a new folder structure with sorted and cleaned files.

## Installation
To use these scripts, you'll need Python 3 and a few additional libraries. You can install the dependencies using:

```sh
pip install -r requirements.txt
```

## Dependencies
- `os` and `shutil` (Standard Python libraries)
- `PyPDF2` (for handling PDF files)

## License
This project is licensed under the MIT License.

## Contributing
Contributions are welcome! Feel free to open issues or submit pull requests to improve the functionality or add new features.

## Contact
If you have any questions or suggestions, feel free to reach out or open an issue on GitHub.