from __future__ import annotations

import re


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    return len(text) // 4


def extract_sections(text: str) -> dict[str, str]:
    """Attempt to extract key sections from a paper using regex header detection."""
    section_patterns = [
        (r'(?i)\b(abstract)\b', "abstract"),
        (r'(?i)\b(introduction)\b', "introduction"),
        (r'(?i)\b(method(?:s|ology)?)\b', "methods"),
        (r'(?i)\b(results?)\b', "results"),
        (r'(?i)\b(discussion)\b', "discussion"),
        (r'(?i)\b(conclusion(?:s)?)\b', "conclusion"),
        (r'(?i)\b(related\s+work)\b', "related_work"),
    ]

    # Find section positions
    found = []
    for pattern, name in section_patterns:
        for match in re.finditer(pattern, text):
            # Only match if it looks like a header (start of line or after newline)
            pos = match.start()
            line_start = text.rfind('\n', 0, pos)
            prefix = text[line_start + 1:pos].strip()
            # Accept if prefix is empty, a number, or a roman numeral
            if not prefix or re.match(r'^[\d.]+$|^[IVXivx]+\.?$', prefix):
                found.append((pos, name))

    if not found:
        return {"full": text}

    found.sort(key=lambda x: x[0])

    sections = {}
    for i, (pos, name) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(text)
        sections[name] = text[pos:end].strip()

    return sections


def chunk_paper(text: str, token_limit: int = 4000) -> str:
    """Chunk a paper down to fit within token limits.

    Strategy:
    - If under limit, return as-is
    - Extract key sections: Abstract + Introduction + Discussion + Conclusion
    - If still over, truncate each section proportionally
    """
    if estimate_tokens(text) <= token_limit:
        return text

    sections = extract_sections(text)

    if "full" in sections:
        # Couldn't parse sections, just truncate
        char_limit = token_limit * 4
        return text[:char_limit] + "\n\n[... truncated ...]"

    # Priority order for sections to keep
    priority = ["abstract", "introduction", "conclusion", "discussion", "methods", "results", "related_work"]
    kept = []
    running_tokens = 0

    for section_name in priority:
        if section_name in sections:
            section_text = sections[section_name]
            section_tokens = estimate_tokens(section_text)

            if running_tokens + section_tokens <= token_limit:
                kept.append(section_text)
                running_tokens += section_tokens
            else:
                # Take what fits
                remaining = token_limit - running_tokens
                if remaining > 200:
                    char_limit = remaining * 4
                    kept.append(section_text[:char_limit] + "\n[... section truncated ...]")
                break

    return "\n\n".join(kept) if kept else text[:token_limit * 4]


def prepare_papers_for_context(
    papers: list[dict],
    max_total_tokens: int = 150_000,
) -> tuple[list[dict], bool]:
    """Prepare paper texts to fit within context limits.

    Returns:
        (prepared_papers, used_digests): papers with text field adjusted,
        and whether digest mode was needed.
    """
    # First pass: estimate total tokens
    total = sum(estimate_tokens(p.get("text", "") or "") for p in papers)

    if total <= max_total_tokens:
        return papers, False

    # Try chunking each paper
    per_paper_limit = max_total_tokens // max(len(papers), 1)
    chunked = []
    for p in papers:
        text = p.get("text", "") or ""
        if text:
            p = {**p, "text": chunk_paper(text, per_paper_limit)}
        chunked.append(p)

    total_after = sum(estimate_tokens(p.get("text", "") or "") for p in chunked)
    if total_after <= max_total_tokens:
        return chunked, False

    # Need digest mode — signal to caller
    return chunked, True
