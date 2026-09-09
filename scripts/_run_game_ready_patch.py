from pathlib import Path

source_path = Path('scripts/_apply_game_ready_patch.py')
source = source_path.read_text(encoding='utf-8')
start = source.index('old_history_tail =')
end = source.index('\n\n# 4)', start)
replacement = '''history_note = '<p className="history-note">'\napp = replace_once(app, history_note, '<PostgameReviews autopsies={autopsies}/>' + history_note, "History reviews insert")'''
patched = source[:start] + replacement + source[end:]
exec(compile(patched, str(source_path), 'exec'), {'__name__': '__main__'})
Path(__file__).unlink(missing_ok=True)
