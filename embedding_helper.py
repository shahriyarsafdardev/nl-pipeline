import re
import uuid
from openai_gpt import create_embedding
from logger import getLogger

link_pattern = r'\s(https?|/[^/\s]+)'
logger = getLogger()


def link_search_text(text):
    pattern = re.compile(link_pattern)

    links = []
    for match in pattern.finditer(text):
        links.append(match.group())

    logger.info(f"links to add as reference: {links}")

    return list(set(links))


def text_slice_to_vector(text, base_url):
    metadata = {
        "text": text,
        "domain_base_url": base_url,
        "referenced_urls": link_search_text(text)
    }

    return (
        str(uuid.uuid4()),
        create_embedding(text),
        metadata
    )

def split_into_chunks(text, max_length=500):
    chunks = []
    current_chunk = ''

    # Split the text by markdown headers
    paragraphs = re.split(r'(\n*#{1,6} .*\n*)', text)
    header_pattern = re.compile(r'\n*(#{1,6}) (.*)\n*')
    header_track = {}

    new_paragraphs = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        header_match = header_pattern.match(paragraph)
        if header_match:
            header_level = len(header_match.group(1))
            header_content = header_match.group(2)    # Get header content

            header_track = {level: header for level,
                            header in header_track.items() if level < header_level}
            header_track[header_level] = header_content
            print(f'Set Title at Level {header_level}: {header_content}')

        else:
            headers = [header for level, header in sorted(
                header_track.items()) if header is not None]
            header_string = '\n'.join(headers)

            if header_string:
                new_paragraphs.append(header_string + "\n" + paragraph)
                print(f'Set Para: {header_string} \n {paragraph}')

    for idx, paragraph in enumerate(new_paragraphs):
        if len(current_chunk) + len(paragraph) + 1 <= max_length:
            current_chunk += "\n"+paragraph
        else:
            # If the current chunk is not empty, append it to the chunks list
            if current_chunk:
                chunks.append(current_chunk)

            # Start a new chunk with the current paragraph
            current_chunk = paragraph

    # Append the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk)

    chunks = [chunk.strip() for chunk in chunks]

    return chunks
