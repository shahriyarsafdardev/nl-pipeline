import re

def detect_links(text):
    # Step 1
    pattern_1 = re.compile(r'<[^>]{0,28}>|{[^}]{0,15}}')
    for match in re.finditer(pattern_1, text):
        if (len(match.group()) <= 30 and '<' in match.group()) or (len(match.group()) <= 17 and '{' in match.group()):
            text = text.replace(match.group(), match.group().replace(" ", "_"))
        
    # Step 2
    pattern_2 = r"(?<=[\s\"'(\[`])(?:http|\/)[^\s\"'\)\]`]+"
    links = re.findall(pattern_2, text)

    # Step 3
    def is_valid_url(url):
        if len(url) <= 2:
            return False
        if '\\' in url:
            return False
        if '\ufffd' in url:
            return False
        if '/' not in url:
            return False
        if len([c for c in url if c.isalpha()]) < 3:
            return False
        return True

    return [link for link in links if is_valid_url(link)]

if __name__ == "__main__":
    example_input = """
    http://api.test.com/<your api key>/<your org id>/test  http://api.test.com/<your api key>/test 
    /test adgahjsgsdj teststring httpstring 
    'http://api.test.com/<your api key>/test'  `http://api.test.com/<your api key>/test` 
    `(/<your api key>/test)`  (/<your api key>/test) {your api key} {your key}
    """

    example_output = [
        "http://api.test.com/<your_api_key>/<your_org_id>/test",
        "http://api.test.com/<your_api_key>/test",
        "/test",
        "http://api.test.com/<your_api_key>/test",
        "http://api.test.com/<your_api_key>/test",
        "/<your_api_key>/test",
        "/<your_api_key>/test",
        "{your_api_key}",
        "{your_key}"
    ]

    assert detect_links(example_input) == example_output

    print(detect_links(example_input))
