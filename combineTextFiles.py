"""Combine text files with relative filenames, without exposing local paths."""
import argparse

from fileutils import atomic_output, input_files

DEFAULT_EXTENSIONS = ['txt', 'md', 'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'json', 'xml', 'yaml', 'yml', 'csv', 'log', 'sh', 'bat', 'java', 'cpp', 'c', 'h', 'hpp', 'swift', 'go', 'rs', 'rb', 'php', 'sql', 'r', 'm', 'scala', 'kt', 'dart', 'lua', 'pl']


def combine_text_files(folder_path, output_file='Combined_Text_Files.txt', extensions=None):
    extensions = DEFAULT_EXTENSIONS if extensions is None else extensions
    extensions = {'.' + ext.lower().lstrip('.') for ext in extensions}
    files, output = input_files(folder_path, output_file, extensions)
    with atomic_output(output) as out:
        for path in files:
            content = path.read_text(encoding='utf-8')
            out.write(f'\n{"=" * 80}\nFILENAME: {path.name}\n')
            out.write(f'FILESIZE: {path.stat().st_size} bytes\n{"=" * 80}\n\n')
            out.write(content)
            if not content.endswith('\n'):
                out.write('\n')
            out.write(f'\n{"=" * 80}\nEND OF FILE: {path.name}\n{"=" * 80}\n\n')
    print(f'Combined {len(files)} file(s) into {output}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder')
    parser.add_argument('-o', '--output', default='Combined_Text_Files.txt')
    parser.add_argument('--extensions', nargs='+')
    args = parser.parse_args()
    combine_text_files(args.folder, args.output, args.extensions)


if __name__ == '__main__':
    main()
