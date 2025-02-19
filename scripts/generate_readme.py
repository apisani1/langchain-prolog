"""Generate README.md from documentation files."""

DOCS_PATH = "../docs/source/"
ELEMENTS = [
    ("badges", "", ""),
    ("home", "", ""),
    ("runnable", "", ""),
    ("tool", "", ""),
]


def extract_content(file_path: str, start_marker: str = None, end_marker: str = None) -> str:
    """Extract content between markers from a file."""
    with open(file_path, "r") as f:
        content = f.read()

    if start_marker and end_marker:
        start = content.find(start_marker)
        end = content.find(end_marker)
        if start != -1 and end != -1:
            return content[start + len(start_marker) : end].strip()
    return content


def generate_readme():
    """Generate README.md from documentation files."""
    # Start with the basic structure
    readme = []

    # Add elements
    for element in ELEMENTS:
        content = extract_content(DOCS_PATH + element[0] + ".md", element[1], element[2])
        readme.append(content)

    # Write the README.md
    with open("../README.md", "w") as f:
        f.write("\n".join(readme))


if __name__ == "__main__":
    generate_readme()
