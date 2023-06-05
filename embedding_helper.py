import re
import uuid
from openai import create_embedding
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
    header_pattern = re.compile(r'(\n*#{1,6} .*\n*)')
    new_paragraphs = []
    current_title = None

    for paragraph in paragraphs:
        if header_pattern.match(paragraph):
            current_title = paragraph
        else:
            if current_title:
                if len(paragraph) <= 500:
                    new_para = current_title + "\n" + paragraph
                    new_paragraphs.append(new_para)

                else:
                    smaller_paragraphs = paragraph.split("\n")
                    merged_paragraph = ''
                    for para in smaller_paragraphs:
                        if len(merged_paragraph) < 500:
                            merged_paragraph += para
                        else:
                            new_merg = current_title + "\n" + merged_paragraph
                            new_paragraphs.append(new_merg)
                            merged_paragraph = ''

                    if merged_paragraph:
                        new_merg = current_title + "\n" + merged_paragraph

                        new_paragraphs.append(new_merg)

                current_title = None

    paragraphs = new_paragraphs

    for idx, paragraph in enumerate(paragraphs):
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
        chunks.append(current_chunk.strip())

    chunks = [f"{chunk.strip()}" for chunk in chunks]

    return chunks
