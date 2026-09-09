from pathlib import Path

for filename, function_name in [
    ('tests/test_editorial_evidence_compositor.py', 'test_qb_history_public_copy_uses_structured_subject_specific_facts'),
    ('tests/test_publication_polish.py', 'test_story_desk_keeps_ordinary_division_rivalry_in_notebook_not_read'),
]:
    path = Path(filename)
    text = path.read_text()
    marker = rf'\n\ndef {function_name}'
    if marker not in text:
        continue
    prefix, tail = text.split(marker, 1)
    tail = (marker + tail).replace(r'\n', '\n')
    path.write_text(prefix + tail)
