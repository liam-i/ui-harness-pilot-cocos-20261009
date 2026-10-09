#!/usr/bin/env python3
"""Run the approved 32-case matrix only on the two dedicated, existing AVDs."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, signal, socket, subprocess, time, traceback, zipfile
import xml.etree.ElementTree as ET

parser=argparse.ArgumentParser()
parser.add_argument('--config',type=Path,required=True)
parser.add_argument('--build',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_suite',P/'tests/cocos-menu/suite.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
c=json.loads(args.config.read_text());build=json.loads(args.build.read_text())
assert build['passed'], 'Actual native build is required'
assert hashlib.sha256(Path(build['apk']['path']).read_bytes()).hexdigest()==build['apk']['sha256'], 'APK identity changed'
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(out/'test-inputs.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for path in [Path(__file__),*sorted((P/'tests/cocos-menu').glob('*.py')),*sorted((P/'tests/cocos-menu').glob('*.json'))]:
        archive.write(path,path.relative_to(P))
expected=json.loads((P/'tests/cocos-menu/expected.json').read_text())
env=dict(os.environ,ANDROID_USER_HOME=c['android_user'],ANDROID_EMULATOR_HOME=c['emulator_home'],
         ANDROID_AVD_HOME=c['avds'],ANDROID_SDK_ROOT=c['sdk'],
         ANDROID_ADB_SERVER_PORT='5038',ADB_SERVER_SOCKET='tcp:127.0.0.1:5038')
adb=[c['sdk']+'/platform-tools/adb','-P','5038']
record={'started_at':time.time(),'build':str(args.build),'apk':build['apk'],
        'expected_cases':32,'devices':[],'passed':False,'cleanup_errors':[]}
processes=[];settings=[];server_started=False

def save(): (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')

def interrupted(number, frame):
    signal.signal(signal.SIGTERM,signal.SIG_IGN)
    signal.signal(signal.SIGINT,signal.SIG_IGN)
    record['interrupted']=True
    raise InterruptedError('Runtime interrupted by signal '+str(number))

signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)

def run(command,limit=15):
    r=subprocess.run(command,env=env,capture_output=True,text=True,timeout=limit)
    if r.returncode:raise RuntimeError(str(command)+': '+r.stderr)
    return r.stdout.strip()

try:
    # Register cleanup before starting any owned process. Do not attach to occupied ports.
    for port in [5038,5580,5581,5582,5583]:
        with socket.socket() as sock:sock.bind(('127.0.0.1',port))
    run(adb+['start-server']);server_started=True
    for index,device in enumerate(expected['devices']):
        serial='emulator-'+str(5580+index*2)
        item={'name':device['name'],'serial':serial,'boot_started_at':time.time(),'cases':[]}
        record['devices'].append(item);save()
        cmd=[c['sdk']+'/emulator/emulator','-avd',device['name'],'-port',str(5580+index*2),
             '-no-window','-no-audio','-no-snapshot','-no-boot-anim','-gpu','swiftshader']
        with (out/(serial+'.log')).open('wb') as log:
            process=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        processes.append((serial,process));item.update(pid=process.pid,boot_command=cmd);save()
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Emulator exited '+str(process.returncode))
            r=subprocess.run(adb+['-s',serial,'shell','getprop','sys.boot_completed'],env=env,capture_output=True,text=True,timeout=10)
            if r.returncode==0 and r.stdout.strip()=='1':break
            time.sleep(1)
        else:raise TimeoutError('240-second boot limit')
        suite=module.Suite(adb,env,serial,out/serial,device,build,P)
        item['boot_completed_at']=time.time()
        actual={key:suite.shell(*command) for key,command in {
            'fingerprint':['getprop','ro.build.fingerprint'],'api':['getprop','ro.build.version.sdk'],
            'abi':['getprop','ro.product.cpu.abi'],'page_size':['getconf','PAGE_SIZE'],
            'size':['wm','size'],'density':['wm','density']}.items()}
        item['identity']=actual
        assert actual['fingerprint']==expected['runtime']['fingerprint']
        assert int(actual['api'])==37 and actual['abi']=='arm64-v8a' and int(actual['page_size'])==16384
        assert actual['size']=='Physical size: '+str(device['px'][0])+'x'+str(device['px'][1])
        assert actual['density']=='Physical density: '+str(device['density'])
        original={k:suite.shell('settings','get','system',k) for k in ['font_scale','accelerometer_rotation','user_rotation']}
        settings.append((serial,original));item['original_settings']=original;save()
        for key,value in [('font_scale','1.0'),('accelerometer_rotation','0'),('user_rotation','0')]:
            suite.shell('settings','put','system',key,value)
        suite.command(['install','-r',build['apk']['path']],limit=60)
        suite.shell('am','start','-W','-n',module.ACTIVITY)
        # Normally dismiss Android's first full-screen notice; preserve the notice and action.
        suite.shell('uiautomator','dump','/sdcard/window.xml',limit=20)
        xml=suite.shell('cat','/sdcard/window.xml');(suite.out/'initial-window.xml').write_text(xml)
        for node in ET.fromstring(xml).iter('node'):
            if node.get('text') in ['Got it','GOT IT']:
                import re
                suite.screenshot('initial-os-notice',{'state':None})
                bounds=list(map(int,re.findall(r'\d+',node.get('bounds',''))))
                assert len(bounds)==4
                suite.shell('input','tap',str((bounds[0]+bounds[2])//2),str((bounds[1]+bounds[3])//2))
                item['os_notice_dismissed']=True
        try:
            item['cases']=suite.run()
        finally:
            item['cases']=suite.cases
            try:
                (suite.out/'logcat.txt').write_text(suite.command(['logcat','-d','-v','threadtime','-t','3000']))
                suite.screenshot('final-or-failure',{'state':None})
            except Exception as error:item['diagnostic_error']=str(error)
            suite.save();save()
    pairs={(d['name'],case['id']) for d in record['devices'] for case in d['cases'] if case['status']=='passed'}
    required={(d['name'],case['id']) for d in expected['devices'] for case in expected['cases']}
    assert pairs==required and len(pairs)==32
    record['passed']=True
except Exception as error:
    record.update(error=str(error),traceback=traceback.format_exc())
finally:
    for serial,original in settings:
        try:
            for key,value in original.items():
                args_=['delete','system',key] if value=='null' else ['put','system',key,value]
                run(adb+['-s',serial,'shell','settings']+args_)
                restored=run(adb+['-s',serial,'shell','settings','get','system',key])
                assert restored==value,(key,value,restored)
        except Exception as error:record['cleanup_errors'].append(str(error))
    for serial,process in processes:
        if process.poll() is None:
            try:
                run(adb+['-s',serial,'emu','kill']);process.wait(timeout=20)
            except Exception as error:
                record['cleanup_errors'].append(str(error));os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    if server_started:
        try:run(adb+['kill-server'])
        except Exception as error:record['cleanup_errors'].append(str(error))
    if record['cleanup_errors']:record['passed']=False
    record['finished_at']=time.time();save()
print(json.dumps({'passed':record['passed'],'error':record.get('error'),
    'passed_cases':sum(case['status']=='passed' for d in record['devices'] for case in d['cases']),
    'cleanup_errors':record['cleanup_errors'],'record':str(out/'result.json')},indent=2))
raise SystemExit(0 if record['passed'] else 1)
