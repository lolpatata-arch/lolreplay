import ast
import string
import unittest
from pathlib import Path
import lolreplay_i18n as i

class LanguageTests(unittest.TestCase):
    def tearDown(self): i.set_language('en_US')
    def test_languages_and_placeholders(self):
        self.assertEqual(len(i.LANGUAGES),9)
        formatter=string.Formatter()
        def fields(s): return sorted((f,spec) for _,f,spec,_ in formatter.parse(s) if f is not None)
        for text, translations in i.CATALOG.items():
            self.assertEqual(set(translations),set(i.LANGUAGES)-{'en_US'},text)
            for locale,value in translations.items():
                self.assertTrue(value, (locale,text))
                self.assertEqual(fields(text),fields(value),(locale,text))
    def test_formatting_and_fallback(self):
        for locale in i.LANGUAGES:
            i.set_language(locale)
            self.assertIn('90',i.t('{0} sec',90))
            self.assertIn('example.mp4',i.t('Move {0} to the system trash?','example.mp4'))
            self.assertIn('3',i.clip_count(3))
        self.assertEqual(i.set_language('invalid'),'en_US')
        self.assertEqual(i.t('untranslated technical message'),'untranslated technical message')
    def test_ui_translation_keys(self):
        for name in ('lolreplay-ui','lolreplay_editor.py','lolreplay_update_ui.py'):
            tree=ast.parse(Path(__file__).with_name(name).read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='t' and n.args and isinstance(n.args[0],ast.Constant):
                    self.assertIn(n.args[0].value,i.CATALOG,(name,n.lineno))

class TranslationScopeTests(unittest.TestCase):
    def test_translation_function_not_shadowed(self):
        import symtable
        def check(table):
            if table.get_type() == 'function' and 't' in table.get_identifiers():
                symbol = table.lookup('t')
                # Local variables named t are harmless if not called; inspect those below.
                if symbol.is_local() and symbol.is_referenced():
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno == table.get_lineno():
                            calls = [n.lineno for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 't']
                            self.assertFalse(calls, (name, node.name, calls))
            for child in table.get_children():
                check(child)
        for name in ('lolreplay-ui', 'lolreplay_editor.py'):
            source = Path(__file__).with_name(name).read_text()
            tree = ast.parse(source)
            check(symtable.symtable(source, name, 'exec'))
