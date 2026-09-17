"""Combine Markdown files without including the previous output."""
import argparse

from fileutils import atomic_output, input_files


def combine_markdown_files(folder_path, output_file='All Markdown.md'):
    files, output = input_files(folder_path, output_file, {'.md'})
    with atomic_output(output) as out:
        for path in files:
            out.write(f'# {path.name}\n\n{path.read_text(encoding="utf-8")}\n\n')
    print(f'Combined markdown files saved to: {output}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder')
    parser.add_argument('-o', '--output', default='All Markdown.md')
    args = parser.parse_args()
    combine_markdown_files(args.folder, args.output)


if __name__ == '__main__':
    main()
