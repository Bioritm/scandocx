
def context_slice(s: str, pos: int, radius: int = 60) -> str:
    a = max(0, pos - radius)
    b = min(len(s), pos + radius)
    return s[a:b].replace("\n", " ")

def split_paragraphs_from_txt(text: str):
    import re
    parts = re.split(r'(?:\r?\n){2,}', text)
    return [p.strip('\n\r') for p in parts if p.strip() != ""]
