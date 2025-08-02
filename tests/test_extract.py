from pathlib import Path
import ast


def load_extract_featured_artists():
    module_path = Path(__file__).resolve().parents[1] / 'merge youtube Music likes into Spotify.py'
    source = module_path.read_text(encoding='utf-8')
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'extract_featured_artists':
            func_code = ast.get_source_segment(source, node)
            namespace = {}
            exec('import re\n' + func_code, namespace)
            return namespace['extract_featured_artists']
    raise RuntimeError('extract_featured_artists not found')


def test_extract_featured_artists():
    func = load_extract_featured_artists()
    assert func("Song (feat. Artist)") == ("Song", ["Artist"])
