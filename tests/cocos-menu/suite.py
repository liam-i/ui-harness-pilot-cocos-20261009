"""Independent native assertions: inputs are touches/keys; observations are read-only."""
from pathlib import Path
import hashlib, json, re, subprocess, time, traceback, xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).parent))
from png_pixel import pixel

PACKAGE = 'io.harness.cocosmenu'
ACTIVITY = PACKAGE + '/com.cocos.game.AppActivity'

class Suite:
    def __init__(self, adb, env, serial, out, device, build, project):
        self.adb = adb + ['-s', serial]
        self.env, self.out, self.device, self.build, self.project = env, out, device, build, project
        self.out.mkdir(parents=True)
        self.commands, self.cases, self.shots = [], [], []
        self.current = None
        self.case_deadline = self.suite_deadline = float('inf')
        self.seq = 0

    def command(self, args, check=True, binary=False, limit=10):
        remaining = min(self.case_deadline, self.suite_deadline) - time.monotonic()
        if remaining <= 0: raise TimeoutError('Approved case/suite timeout reached')
        start = time.time()
        r = subprocess.run(self.adb + args, env=self.env, capture_output=True,
                           timeout=min(limit, remaining))
        self.commands.append({'case': self.current, 'args': args, 'started_at': start, 'exit': r.returncode,
                              'stdout': '<binary>' if binary else r.stdout.decode(errors='replace'),
                              'stderr': r.stderr.decode(errors='replace')})
        if check and r.returncode: raise RuntimeError('adb failed: ' + str(args) + ': ' + r.stderr.decode(errors='replace'))
        return r.stdout if binary else r.stdout.decode(errors='replace').strip()

    def shell(self, *args, **kw): return self.command(['shell', *args], **kw)

    def observe(self, predicate=lambda x: True, after=0):
        deadline = min(self.case_deadline, self.suite_deadline, time.monotonic() + 12)
        latest = None
        while time.monotonic() < deadline:
            raw = self.shell('run-as', PACKAGE, 'cat', 'files/menu-observation.json', check=False)
            try: latest = json.loads(raw)
            except (ValueError, TypeError): latest = None
            if latest and latest['capturedAt'] > after and latest['frame'] > 2 and latest.get('viewport'):
                if predicate(latest):
                    self.seq += 1
                    (self.out / f'observation-{self.seq:03}.json').write_text(json.dumps(latest, indent=2) + '\n')
                    return latest
            time.sleep(0.1)
        raise AssertionError('Expected fresh native observation; latest=' + json.dumps(latest and latest.get('state')))

    def state(self, screen='menu', best=128, session=None, dialog=False, after=0):
        expected = dict(screen=screen, best=best, sessionId=session, dialogOpen=dialog)
        return self.observe(lambda o: o['state'] == expected, after)

    def cold(self):
        self.shell('am', 'force-stop', PACKAGE)
        # Remove only the stale observation, never inject business state.
        self.shell('run-as', PACKAGE, 'rm', '-f', 'files/menu-observation.json')
        self.shell('am', 'start', '-W', '-n', ACTIVITY)
        return self.state()

    def node(self, observation, name):
        found = [n for n in observation['nodes'] if n['name'] == name]
        assert len(found) == 1, (name, len(found))
        return found[0]

    def touch(self, x, y, observation):
        scale = observation['frameSize']['width'] / 375
        self.shell('input', 'tap', str(round(x * scale)), str(round(y * scale)))
        return observation['capturedAt']

    def tap(self, name, o):
        r = self.node(o, name)['rect']
        return self.touch(r['x'] + r['width'] / 2, r['y'] + r['height'] / 2, o)

    def key(self, key): self.shell('input', 'keyevent', key)

    def screenshot(self, name, o):
        data = self.command(['exec-out', 'screencap', '-p'], binary=True)
        assert data.startswith(b'\x89PNG\r\n\x1a\n')
        path = self.out / (name + '.png'); path.write_bytes(data)
        self.shots.append({'case': self.current, 'path': path.name,
                           'sha256': hashlib.sha256(data).hexdigest(), 'state': o['state']})
        if o.get('state') is not None:
            expected = (176,172,162) if o['state']['dialogOpen'] else (250,247,239)
            actual = pixel(data,10,10)
            assert all(abs(a-b)<=1 for a,b in zip(actual,expected)), ('rendered backdrop/background',actual,expected)

    def assert_menu(self, o, enabled):
        assert o['scene'] == 'Menu' and o['package'] == PACKAGE
        assert o['sceneUuid'] == self.build['scene_uuid']
        b = self.node(o, 'continue')
        assert b['button']['interactable'] == enabled
        assert abs(b['opacity'] - (1 if enabled else 0.45)) <= 1/255
        assert self.node(o, 'best')['label']['text'] == str(o['state']['best'])

    def geometry(self, o):
        assert o['profilerVisible'] is False, 'Debug statistics obscure approved UI'
        height = o['visible']['height']; width = o['visible']['width']
        assert abs(width - 375) < 0.01
        assert o['frameSize']['width'] == self.device['px'][0]
        assert o['frameSize']['height'] == self.device['px'][1]
        assert abs(height - self.device['px'][1] * 375 / self.device['px'][0]) < 0.1
        assert o['viewport']['orientation'] == 1
        scale = self.device['px'][0] / 375
        safe = o['viewport']['safeInsets']
        buttons = [n for n in o['nodes'] if n['button']]
        if o['state']['dialogOpen']: buttons = [n for n in buttons if n['name'] in ['cancel', 'confirm-reset']]
        for n in buttons:
            r = n['rect']; required = 50 if n['name'] == 'reset-best' else 64
            assert r['height'] >= required - 0.01, (n['name'], r)
            assert r['x'] >= max(24, safe['left']/scale) - 0.01
            assert r['x'] + r['width'] <= min(351, width-safe['right']/scale) + 0.01
            assert r['y'] >= safe['top']/scale - 0.01
            assert r['y'] + r['height'] <= height-safe['bottom']/scale + 0.01
        for i, a in enumerate(buttons):
            for b in buttons[i+1:]:
                x,y=a['rect'],b['rect']
                overlap_x=min(x['x']+x['width'],y['x']+y['width'])-max(x['x'],y['x'])
                overlap_y=min(x['y']+x['height'],y['y']+y['height'])-max(x['y'],y['y'])
                assert min(overlap_x,overlap_y) <= 0.01, ('overlapping controls',a['name'],b['name'])
        for n in o['nodes']:
            if n['label']:
                r=n['rect']; assert r['x'] >= -0.01 and r['y'] >= -0.01 and r['x']+r['width'] <= width+0.01 and r['y']+r['height'] <= height+0.01, n
                if '/eyebrow/' in n['path']: assert n['label']['fontSize']==11
                if '/title/' in n['path']: assert n['label']['fontSize']==92
                if '/score-caption/' in n['path']: assert n['label']['fontSize']==10
                if '/session-title/' in n['path'] or '/reset-title/' in n['path']: assert n['label']['fontSize']==28
                if n['path'].endswith('/label'):
                    expected_size=17 if any('/'+b+'/' in n['path'] for b in ['cancel','confirm-reset']) else 15 if '/reset-best/' in n['path'] else 19
                    assert n['label']['fontSize']==expected_size
        if o['state']['dialogOpen']: assert self.node(o,'modal-backdrop')['graphics']['fill']=='423b2e66'
        if o['state']['screen'] == 'menu':
            top = 36 if height <= 700 else 70
            nav = top + 259.625 + (26 if height <= 700 else 38)
            for name, y in [('continue',nav), ('new-game',nav+80), ('reset-best',nav+160)]:
                r=self.node(o,name)['rect']
                assert abs(r['x']-31.5)*scale <= 1 and abs(r['width']-312)*scale <= 1, (name,r)
                assert abs(r['y']-y)*scale <= 1, (name,r,y)
            assert self.node(o,'best')['label']['fontSize'] == 30
            assert self.node(o,'tagline')['label']['text'] == 'Make room for your next move.'
            # Independent reference DOM centers; the existing SYSTEM-GLYPHS tolerance is 2 units.
            for name,cx,cy in [('spark',286.1,top+38.125),('arrow',305.371,nav+112)]:
                r=self.node(o,name)['rect']
                assert abs(r['x']+r['width']/2-cx)<=2 and abs(r['y']+r['height']/2-cy)<=2, ('text decoration center',name,r)
        else:
            assert self.node(o,'session-copy')['label']['text'] == 'Session started.'
            assert [self.node(o,'tile-value-'+str(i))['label']['text'] for i in range(2)] == ['2','2']
        assert self.node(o,'footer')['label']['fontSize'] == 12

    def new_and_menu(self, o):
        t=self.tap('new-game',o); s=self.observe(lambda v:v['state']['screen']=='session',t)
        session=s['state']['sessionId']; assert isinstance(session,int) and session>0
        t=self.tap('menu-back',s)
        return self.state(best=s['state']['best'],session=session,after=t),session

    def reset(self,o,session=None):
        t=self.tap('reset-best',o); d=self.state(best=o['state']['best'],session=session,dialog=True,after=t)
        t=self.tap('confirm-reset',d)
        return self.state(best=0,session=session,after=t)

    def walk_states(self,prefix):
        seen=set(); o=self.cold()
        def keep(name,obj):
            self.geometry(obj); self.screenshot(prefix+'-'+name.replace('/','-'),obj); seen.add(name)
        keep('menu/default',o)
        t=self.tap('reset-best',o); d=self.state(dialog=True,after=t);keep('dialog/reset-empty',d)
        t=self.tap('confirm-reset',d);o=self.state(best=0,after=t);keep('menu/zero-empty',o)
        t=self.tap('reset-best',o);d=self.state(best=0,dialog=True,after=t);keep('dialog/reset-empty-zero',d)
        t=self.tap('cancel',d);o=self.state(best=0,after=t)
        o,sid=self.new_and_menu(o);keep('menu/zero-resumable',o)
        t=self.tap('reset-best',o);d=self.state(best=0,session=sid,dialog=True,after=t);keep('dialog/reset-resumable-zero',d)
        t=self.tap('cancel',d);o=self.state(best=0,session=sid,after=t)
        o,sid=self.new_and_menu(self.cold());keep('menu/resumable',o)
        t=self.tap('reset-best',o);d=self.state(session=sid,dialog=True,after=t);keep('dialog/reset-resumable',d)
        t=self.tap('cancel',d);o=self.state(session=sid,after=t)
        t=self.tap('continue',o);s=self.state(screen='session',session=sid,after=t);keep('session/active',s)
        assert set(json.loads((Path(__file__).parent/'expected.json').read_text())['required_states']) <= seen

    def case(self,id):
        if id=='C01':
            o=self.cold();self.assert_menu(o,False);self.geometry(o);self.screenshot('C01-cold',o)
        elif id=='C02':
            o=self.cold();t=self.tap('continue',o);self.assert_menu(self.state(after=t),False)
        elif id=='C03':
            o,sid=self.new_and_menu(self.cold());self.assert_menu(o,True)
        elif id=='C04':
            o,sid=self.new_and_menu(self.cold());t=self.tap('continue',o);self.state(screen='session',session=sid,after=t)
        elif id=='C05':
            o=self.cold();t=self.tap('reset-best',o);d=self.state(dialog=True,after=t)
            t=self.touch(10,10,d);d=self.state(dialog=True,after=t)
            t=self.tap('cancel',d);self.state(after=t)
        elif id=='C06':
            o=self.reset(self.cold());self.assert_menu(o,False);self.screenshot('C06-zero-empty',o)
        elif id=='C07':
            o,sid=self.new_and_menu(self.cold());o=self.reset(o,sid);self.assert_menu(o,True)
            self.screenshot('C07-zero-resumable',o);t=self.tap('continue',o);self.state(screen='session',best=0,session=sid,after=t)
        elif id=='C08':
            o=self.reset(self.cold());t=self.tap('new-game',o);self.state(screen='session',best=0,session=1,after=t)
        elif id=='C09':
            o,sid=self.new_and_menu(self.cold());t=self.tap('reset-best',o);d=self.state(session=sid,dialog=True,after=t)
            self.key('KEYCODE_BACK');o=self.state(session=sid,after=d['capturedAt'])
            assert o['nativeBackCount']==d['nativeBackCount']+1
        elif id=='C10':
            o=self.cold();t=self.tap('new-game',o);s=self.state(screen='session',session=1,after=t)
            self.key('KEYCODE_BACK');o=self.state(session=1,after=s['capturedAt']);self.assert_menu(o,True)
            assert o['nativeBackCount']==s['nativeBackCount']+1
        elif id=='C11':
            o=self.cold();self.key('KEYCODE_BACK')
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                focus=self.shell('dumpsys','window','windows')
                blocks=re.split(r'(?m)^  Window #',focus)[1:]
                app_windows=[b for b in blocks if PACKAGE+'/com.cocos.game.AppActivity' in b.splitlines()[0]]
                launcher=[b for b in blocks if 'com.google.android.apps.nexuslauncher/' in b.splitlines()[0]]
                current={'app_windows':app_windows,'launcher_windows':launcher}
                if app_windows and launcher and all('isOnScreen=false' in b and 'isVisible=false' in b for b in app_windows) and any('isOnScreen=true' in b and 'isVisible=true' in b for b in launcher):break
                time.sleep(0.1)
            else:raise AssertionError('Back did not leave foreground')
            self.state_after_leave=current;self.cold()
        elif id=='C12':
            o,sid=self.new_and_menu(self.cold());o=self.reset(o,sid);pid=o['pid'];self.key('KEYCODE_HOME')
            assert self.shell('pidof',PACKAGE)==str(pid)
            self.shell('am','start','-W','-n',ACTIVITY)
            new=self.state(best=0,session=sid,after=o['capturedAt']);assert new['pid']==pid
        elif id=='C13':
            o=self.cold()
            for name,sha in [('primary','0c43a01a95270167be8c05a68c45a2709e60177d9dfa59bedb56fd0802659e52'),('secondary','f0f3d52f110768bf93a10b44f4ec3c727924c25734ce85e1275464c9b02cfe18')]:
                rel='assets/resources/ui/menu/menu-'+name+'.png'
                assert hashlib.sha256((self.project/rel).read_bytes()).hexdigest()==sha
                assert self.build['source_files'][rel]==sha
                uuid=self.build['imported_resources'][rel+'.meta']['subMetas']['f9941']['uuid']
                sprites=[n for n in o['nodes'] if n['sprite'] and n['sprite']['uuid']==uuid]
                assert sprites and all(s['sprite']['insets']==[32,32,32,32] for s in sprites)
                assert all(s['sprite']['original']=={'width':384,'height':128} for s in sprites)
            assert o['tokensUuid']==self.build['imported_resources']['assets/resources/ui/menu/tokens.json.meta']['uuid']
        elif id=='C14':self.walk_states('C14')
        elif id=='C15':
            self.shell('settings','put','system','font_scale','1.3')
            self.walk_states('C15-font130')
            o=self.observe();assert abs(o['viewport']['fontScale']-1.3)<0.001
            self.shell('settings','put','system','font_scale','1.0')
            assert self.shell('settings','get','system','font_scale')=='1.0'
        elif id=='C16':
            self.shell('settings','put','system','accelerometer_rotation','0')
            self.shell('settings','put','system','user_rotation','1')
            o=self.cold();self.geometry(o);self.screenshot('C16-requested-landscape',o)
            self.shell('settings','put','system','user_rotation','0')
            assert self.shell('settings','get','system','user_rotation')=='0'
        else:raise AssertionError('Unknown case '+id)

    def run(self):
        self.suite_deadline=time.monotonic()+300
        expected=json.loads((Path(__file__).parent/'expected.json').read_text())
        try:
            for case in expected['cases']:
                self.current=case['id'];self.case_deadline=time.monotonic()+30
                item={'id':self.current,'started_at':time.time(),'status':'running'};self.cases.append(item)
                try:self.case(self.current);item['status']='passed'
                except Exception as error:
                    item.update(status='failed',error=str(error),traceback=traceback.format_exc())
                    raise
                finally:
                    item['finished_at']=time.time();self.save()
        finally:
            self.case_deadline=self.suite_deadline=float('inf');self.save()
        return self.cases

    def save(self):
        (self.out/'cases.json').write_text(json.dumps({'device':self.device,'cases':self.cases,'screenshots':self.shots},indent=2)+'\n')
        (self.out/'commands.json').write_text(json.dumps(self.commands,indent=2)+'\n')
