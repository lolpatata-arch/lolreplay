import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile
import lolreplay_updater as u
import install


def release(tag='v1.9.0',preview=False,data=b'x'):
    name=f'lolreplay-{tag}.zip'
    return {'tag_name':tag,'draft':False,'prerelease':preview,'body':'Changes','assets':[{'name':name,'browser_download_url':f'https://github.com/{u.REPO}/releases/download/{tag}/{name}','state':'uploaded','size':len(data),'digest':'sha256:'+hashlib.sha256(data).hexdigest()}]}

def archive(extra=None):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for name in ('install.py','lolreplay','lolreplay-ui','crimson-clips','lolreplay.png','lolreplay_updater.py'):
            z.writestr('lolreplay-1.9.0/'+name, "print('lolreplay 1.9.0')" if name=='lolreplay' else 'test')
        if extra: z.writestr(extra,'bad')
    return out.getvalue()

class UpdaterTests(unittest.TestCase):
    def test_release_filters(self):
        draft=release('v2.0.0'); draft['draft']=True
        missing=release('v3.0.0'); missing['assets'][0]['digest']=None
        bad=release('v4.0.0'); bad['assets'][0]['browser_download_url']='https://example.org/a.zip'
        items=[release('v1.9.0'),release('v1.10.0'),release('v1.11.0',True),release('v1.2.0'),release('v1.0.0'),draft,missing,bad]
        self.assertEqual([r['tag'] for r in u.releases(items)],['v1.10.0','v1.9.0'])
        self.assertEqual(u.releases(items,True)[0]['tag'],'v1.11.0')
    def test_integrity_and_paths(self):
        with tempfile.TemporaryDirectory() as d:
            data=archive(); r=u.releases([release(data=data)])[0]
            self.assertTrue((u.extract(data,r,Path(d))/'install.py').is_file())
            with self.assertRaises(u.UpdateError): u.extract(data+b'x',r,Path(d))
        for name in ('../escape','lolreplay-1.9.0/../escape','/tmp/escape','lolreplay-1.9.0/.git/config'):
            with tempfile.TemporaryDirectory() as d:
                data=archive(name); r=u.releases([release(data=data)])[0]
                with self.assertRaises(u.UpdateError): u.extract(data,r,Path(d))
    def test_no_install_without_confirmation(self):
        with patch.object(u,'available',return_value=u.releases([release()])), patch.object(u,'install_release') as action, patch('builtins.input',return_value='n'):
            self.assertEqual(u.main(['v1.9.0']),0); action.assert_not_called()
            self.assertEqual(u.main(['v1.9.0','--yes']),1); action.assert_not_called()
    def test_recorder_guard_and_changed_digest(self):
        with patch.object(u,'stopped',side_effect=u.UpdateError('running')), patch.object(u,'available') as check:
            with self.assertRaises(u.UpdateError): u.install_release('v1.9.0')
            check.assert_not_called()
        with patch.object(u,'stopped'), patch.object(u,'available',return_value=u.releases([release()])), patch.object(u,'fetch') as download:
            with self.assertRaises(u.UpdateError): u.install_release('v1.9.0',digest='changed')
            download.assert_not_called()
    def test_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d); bin=home/'bin'; bin.mkdir(); original=bin/'lolreplay'; original.write_text('old')
            def fail():
                original.write_text('new'); (bin/'lolreplay-ui').write_text('new'); raise OSError('simulated failure')
            with patch.object(install,'BIN',bin),patch.object(install,'DATA',home/'data'),patch.object(install,'install_locked',side_effect=fail):
                with self.assertRaises(OSError): install.transactional_install()
            self.assertEqual(original.read_text(),'old'); self.assertFalse((bin/'lolreplay-ui').exists())
    def test_download_hosts(self):
        for url in ('http://github.com/x','https://github.com.evil.test/x','https://example.org/x','https://user@github.com/x'):
            with self.assertRaises(u.UpdateError): u.trusted(url)
    def test_install_contract(self):
        data=archive()
        with patch.object(u,'stopped'), patch.object(u,'available',return_value=u.releases([release(data=data)])), patch.object(u,'fetch',return_value=data),patch.object(u.subprocess,'run') as run:
            run.return_value.returncode=0; run.return_value.stdout='ok';run.return_value.stderr=''
            r=u.releases([release(data=data)])[0];u.install_release(r['tag'],digest=r['digest']);self.assertEqual(run.call_count,2)
            self.assertEqual(run.call_args.args[0][-3:],['--update','--from-version',u.VERSION])
