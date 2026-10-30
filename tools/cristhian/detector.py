"""Inicia, consulta y detiene el detector; todos los archivos son locales a resultados/."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from uuid import uuid4

REPO=Path(__file__).resolve().parents[2]
RUNTIME=REPO/'resultados'/'detector'
STATE=RUNTIME/'estado.json'


def process_stamp(pid):
    """Fecha de creación del proceso vivo; evita confundir un PID reutilizado en Windows."""
    if os.name!='nt':
        try:os.kill(pid,0);return str(pid)
        except (ProcessLookupError,PermissionError):return None
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return None
    try:
        exit_code=wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle,ctypes.byref(exit_code)) or exit_code.value!=259:return None
        times=[wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle,*[ctypes.byref(t) for t in times]):return None
        return str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
    finally:kernel.CloseHandle(handle)


def load_state():
    if not STATE.exists():return {}
    return json.loads(STATE.read_text(encoding='utf-8'))


def running(state):
    return bool(state and state.get('stamp') and process_stamp(state['pid'])==state['stamp']
                and not Path(state['done']).exists())


def environment():
    env=os.environ.copy()
    env['PYTHONPATH']=os.pathsep.join(str(REPO/p) for p in ['shared','deteccion'])
    env['PYTHONUNBUFFERED']='1'
    credentials=REPO/'infra/runtime/clientes/deteccion.env'
    for line in credentials.read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key,value=line.split('=',1);env[key.strip()]=value.strip()
    return env


def detector_command(config,output,stop=None):
    command=[sys.executable,'-u','-m','cysa_detector.run','--config',str(config),
             '--salida-conteos',str(output)]
    if stop:command+=['--stop-file',str(stop)]
    return command



def foreground(config,output):
    """El detector libera la cámara antes del editor; después recarga su YAML."""
    import yaml
    env=environment()
    while True:
        result=subprocess.call(detector_command(config,output),cwd=REPO,env=env)
        if result!=20:return result
        settings=yaml.safe_load(config.read_text(encoding='utf-8'))
        count=max(1,min(8,len(settings.get('lanes',[])) or 3))
        lanes=settings.get('lanes',[])
        direction=lanes[0].get('direction','negative_to_positive') if lanes else 'negative_to_positive'
        access=lanes[0].get('acceso','N') if lanes else 'N'
        result=subprocess.call([sys.executable,str(REPO/'tools/cristhian/calibrar_via.py'),
            '--config',str(config),'--carriles',str(count),'--acceso',access,'--direction',direction],cwd=REPO,env=env)
        if result:return result
        # Guardar y cancelar vuelven al detector; cancelar conserva el YAML anterior.


def start(args):
    import yaml
    state=load_state()
    if running(state):raise SystemExit('Ya hay un detector en segundo plano. Usa detener antes de iniciar otro.')
    config=args.config.resolve();output=args.salida.resolve()
    if not args.segundo_plano:
        try:return foreground(config,output)
        except KeyboardInterrupt:return 130
    RUNTIME.mkdir(parents=True,exist_ok=True)
    lock=RUNTIME/'inicio.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise SystemExit('Hay otro inicio en curso; revisa resultados/detector/inicio.lock si quedó un cierre abrupto.')
    try:
        if running(load_state()):raise SystemExit('Ya hay un detector en segundo plano.')
        token=uuid4().hex
        runtime_config=RUNTIME/f'{token}.yaml'
        settings=yaml.safe_load(config.read_text(encoding='utf-8'));settings['show']=False
        runtime_config.write_text(yaml.safe_dump(settings,allow_unicode=True,sort_keys=False),encoding='utf-8')
        stop=RUNTIME/f'{token}.stop';done=RUNTIME/f'{token}.done';log=RUNTIME/f'{token}.log'
        command=[sys.executable,str(Path(__file__).resolve()),'_worker','--config',str(runtime_config),
                 '--salida',str(output),'--stop',str(stop),'--done',str(done)]
        with log.open('w',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=REPO,env=environment(),stdin=subprocess.DEVNULL,
                stdout=stream,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        state=dict(pid=process.pid,stamp=process_stamp(process.pid),stop=str(stop),done=str(done),log=str(log),salida=str(output))
        STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            text=log.read_text(encoding='utf-8',errors='replace')
            if process.poll() is not None:
                print(text[-3000:]);return process.returncode or 1
            if 'Resolucion recibida:' in text:
                print('Cámara abierta; detector sin ventana. Esperar la calibración si está en modo automático.')
                print(f'Registro: {log}');return 0
            time.sleep(.5)
        print(f'Proceso creado, sin confirmar imagen todavía. Registro: {log}')
        return 0
    finally:os.close(fd);lock.unlink(missing_ok=True)


def stop(args):
    state=load_state()
    if not running(state):print('No hay un detector gestionado activo.');return 0
    Path(state['stop']).touch()
    deadline=time.monotonic()+args.espera
    while running(state) and time.monotonic()<deadline:time.sleep(.2)
    if running(state):
        print('Parada solicitada. La captura, inferencia o publicación actual todavía no termina. No se forzó el cierre.');return 1
    print('Detector detenido. Los conteos previos se conservan.');return 0


def status():
    state=load_state()
    print('Proceso activo' if running(state) else 'Sin proceso gestionado activo')
    if state:
        log=Path(state['log'])
        print(f'Registro: {log}')
        if log.exists():print('\n'.join(log.read_text(encoding='utf-8',errors='replace').splitlines()[-12:]))
    return 0


def worker(args):
    # El archivo done acredita la finalización aun si fallan MQTT, la cámara o el modelo.
    try:return subprocess.call(detector_command(args.config,args.salida,args.stop),cwd=REPO)
    finally:args.done.touch()


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('iniciar');a.add_argument('--config',type=Path,default=REPO/'deteccion/config/carriles_cristhian.yaml')
    a.add_argument('--salida',type=Path,default=REPO/'resultados/conteos_s10.csv')
    a.add_argument('--segundo-plano',action='store_true')
    a=sub.add_parser('detener');a.add_argument('--espera',type=float,default=20)
    sub.add_parser('estado')
    a=sub.add_parser('_worker');a.add_argument('--config',type=Path,required=True);a.add_argument('--salida',type=Path,required=True)
    a.add_argument('--stop',type=Path,required=True);a.add_argument('--done',type=Path,required=True)
    args=p.parse_args()
    return start(args) if args.action=='iniciar' else stop(args) if args.action=='detener' else status() if args.action=='estado' else worker(args)

if __name__=='__main__':raise SystemExit(main())
