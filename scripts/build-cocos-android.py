#!/usr/bin/env python3
"""Build the fixed local Creator/Android toolchain and retain every attempt."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, signal, subprocess, time, zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
P = Path(__file__).resolve().parents[1]
c = json.loads(args.config.read_text())
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
record = {'started_at': time.time(), 'project': str(P), 'config': c, 'steps': [], 'passed': False}

def save():
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')

env = dict(os.environ)
env.pop('ELECTRON_RUN_AS_NODE', None)
env.update(JAVA_HOME=c['jdk'], ANDROID_HOME=c['sdk'], ANDROID_NDK_HOME=c['sdk'] + '/ndk/28.2.13676358',
           GRADLE_USER_HOME=c['gradle_cache'], ANDROID_USER_HOME=c['android_user'],
           npm_config_userconfig=c['npmrc'], npm_config_globalconfig=c['npmrc'],
           npm_config_cache=c['npm_cache'], npm_config_audit='false', npm_config_fund='false')
env['PATH'] = c['jdk'] + '/bin:' + env.get('PATH', '')

def run(name, command, cwd, limit, expected):
    step = {'name': name, 'command': command, 'cwd': str(cwd), 'timeout_seconds': limit,
            'expected_exit': expected, 'started_at': time.time()}
    record['steps'].append(step); save()
    with (out / (name + '.stdout')).open('wb') as stdout, (out / (name + '.stderr')).open('wb') as stderr:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        step['pid'] = process.pid; save()
        try:
            step['exit'] = process.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            step['timed_out'] = True
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
            step['exit'] = process.returncode
    step['finished_at'] = time.time(); save()
    if step['exit'] != expected or step.get('timed_out'):
        raise RuntimeError(name + ' failed; original logs retained')

try:
    source_paths = []
    for root in ['assets', 'native', 'settings', 'scripts']:
        source_paths.extend(p for p in (P / root).rglob('*') if p.is_file())
    source_paths += [P / 'package.json', P / 'package-lock.json', P / 'tsconfig.json']
    record['source_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=P, text=True).strip()
    record['source_dirty'] = subprocess.check_output(['git', 'status', '--porcelain'], cwd=P, text=True)
    record['source_files'] = {str(p.relative_to(P)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    with zipfile.ZipFile(out / 'build-input-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in source_paths: archive.write(p, p.relative_to(P))
    scene_id = json.loads((P / 'assets/scenes/Menu.scene.meta').read_text())['uuid']
    options = {
        'name': 'ui-harness-cocos-menu', 'platform': 'android', 'debug': True,
        'buildPath': str(P / 'build'), 'outputName': 'android', 'startScene': scene_id,
        'scenes': [{'url': 'db://assets/scenes/Menu.scene', 'uuid': scene_id}],
        'packages': {
            'android': {'packageName': 'io.harness.cocosmenu', 'apiLevel': 36,
                'orientation': {'portrait': True, 'landscapeRight': False, 'landscapeLeft': False, 'upsideDown': False},
                'appABIs': ['arm64-v8a'], 'useDebugKeystore': True, 'isSoFileCompressed': False,
                'appBundle': False, 'androidInstant': False, 'inputSDK': False, 'resizeableActivity': True,
                'sdkPath': c['sdk'], 'ndkPath': c['sdk'] + '/ndk/28.2.13676358',
                'javaHome': c['jdk'], 'javaPath': c['jdk'] + '/bin/java', 'swappy': False,
                'renderBackEnd': {'vulkan': False, 'gles3': True, 'gles2': False}},
            'native': {'encrypted': False, 'compressZip': False, 'runAfterMake': False,
                'JobSystem': 'none', 'serverMode': False}}}
    options_path = out / 'build-options.json'
    options_path.write_text(json.dumps(options, indent=2) + '\n')
    run('creator', [c['creator'], '--home', c['creator_home'], '--user-data-dir=' + c['electron_data'],
        '--project', str(P), '--build', 'configPath=' + str(options_path) + ';logDest=' + str(out / 'creator.log')], P, 600, 36)
    props = P / 'build/android/proj/gradle.properties'
    original = props.read_text()
    # Exact already verified preflight settings; no wrapper download or SDK auto-install.
    import re
    original = re.sub(r'^PROP_COMPILE_SDK_VERSION=.*$', 'PROP_COMPILE_SDK_VERSION=36', original, flags=re.M)
    original = re.sub(r'^PROP_TARGET_SDK_VERSION=.*$', 'PROP_TARGET_SDK_VERSION=36', original, flags=re.M)
    original = re.sub(r'^PROP_BUILD_TOOLS_VERSION=.*$', 'PROP_BUILD_TOOLS_VERSION=36.0.0', original, flags=re.M)
    original = re.sub(r'^PROP_NDK_VERSION=.*$', 'PROP_NDK_VERSION=28.2.13676358', original, flags=re.M)
    for key, value in [('android.builder.sdkDownload', 'false'), ('org.gradle.workers.max', '2')]:
        original = re.sub(r'^' + re.escape(key) + r'=.*\n?', '', original, flags=re.M)
        original += '\n' + key + '=' + value + '\n'
    props.write_text(original)
    (out / 'gradle.properties').write_text(original)
    run('native', [c['gradle'], '--no-daemon', '--console=plain', 'assembleDebug'], P / 'build/android/proj', 900, 0)
    apks = list((P / 'build/android/proj/build').rglob('outputs/apk/debug/*.apk'))
    if len(apks) != 1: raise RuntimeError('Expected exactly one real debug APK: ' + str(apks))
    apk = apks[0]
    with zipfile.ZipFile(apk) as archive:
        library = archive.read('lib/arm64-v8a/libcocos.so')
        if len(library) < 1000000: raise RuntimeError('Native engine missing')
    retained = out / apk.name
    shutil.copyfile(apk, retained)
    record['apk'] = {'path': str(retained), 'generated_path': str(apk), 'bytes': apk.stat().st_size, 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
                     'native_library_sha256': hashlib.sha256(library).hexdigest()}
    record['imported_resources'] = {str(p.relative_to(P)): json.loads(p.read_text())
        for p in (P / 'assets/resources/ui/menu').glob('*.meta')}
    record['scene_uuid'] = scene_id
    record['passed'] = True
except Exception as error:
    record['error'] = str(error)
finally:
    record['finished_at'] = time.time(); save()
print(json.dumps({k: v for k, v in record.items() if k not in ['source_files', 'imported_resources', 'config', 'source_dirty']}, indent=2))
raise SystemExit(0 if record['passed'] else 1)
