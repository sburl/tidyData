"""Merge PDFs in filename order and report output-size growth."""
import argparse

from pypdf import PdfReader, PdfWriter

from fileutils import atomic_output, input_files


def combine_pdfs(folder_path, output_filename='combined.pdf'):
    files, output = input_files(folder_path, output_filename, {'.pdf'})
    total_size = sum(p.stat().st_size for p in files)
    with PdfWriter() as writer:
        for path in files:
            with path.open('rb') as source:
                reader = PdfReader(source)
                for page in reader.pages:
                    writer.add_page(page)
        with atomic_output(output, binary=True) as out:
            writer.write(out)
    if output.stat().st_size > total_size:
        print('Warning: The combined PDF is larger than the sum of the input files.')
    else:
        print(f'PDFs combined successfully into {output}.')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder')
    parser.add_argument('-o', '--output', default='combined.pdf')
    args = parser.parse_args()
    combine_pdfs(args.folder, args.output)


if __name__ == '__main__':
    main()
