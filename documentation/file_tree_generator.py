import os
import fnmatch


def read_gitignore(gitignore_path):
    ignore_patterns = [".git"]

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith("#"):
                    ignore_patterns.append(stripped_line.rstrip('/'))

    return ignore_patterns


def should_ignore(entry_path, entry, ignore_patterns):
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(entry_path, pattern) or fnmatch.fnmatch(entry, pattern):
            return True
    return False


def generate_file_tree(start_path, ignore_patterns, indent_level=0):
    file_tree = ""

    for entry in sorted(os.listdir(start_path)):
        entry_path = os.path.join(start_path, entry)

        if should_ignore(entry_path, entry, ignore_patterns):
            continue

        if os.path.isfile(entry_path):
            file_tree += f"{'  ' * indent_level}- {entry}\n"
        elif os.path.isdir(entry_path):
            file_tree += f"{'  ' * indent_level}* {entry}\n"
            file_tree += generate_file_tree(entry_path,
                                            ignore_patterns, indent_level + 1)

    return file_tree


def main():
    current_dir = os.getcwd()
    gitignore_path = os.path.join(current_dir, ".gitignore")
    ignore_patterns = read_gitignore(gitignore_path)

    file_tree = generate_file_tree(current_dir, ignore_patterns)

    with open("documentation/file_tree.md", "w") as f:
        f.write(file_tree)


if __name__ == "__main__":
    main()
