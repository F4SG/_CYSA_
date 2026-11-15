"""Inicia, consulta y detiene el detector; todos los archivos son locales a resultados/."""
import argparse,json,os,re,subprocess,sys,time
from copy import deepcopy
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



def edit_lanes(config,env,*,cancelar_inicio=False):
    """Abre el editor de carriles sobre la misma fuente del YAML (cámara o primer cuadro del video)."""
    import yaml
    settings=yaml.safe_load(config.read_text(encoding='utf-8'))
    lanes=settings.get('lanes',[])
    count=max(1,min(8,len(lanes) or 3))
    direction=lanes[0].get('direction','negative_to_positive') if lanes else 'negative_to_positive'
    access=lanes[0].get('acceso','N') if lanes else 'N'
    command = [sys.executable, str(REPO/'tools/cristhian/calibrar_via.py'),
               '--config', str(config), '--carriles', str(count), '--acceso', access, '--direction', direction]
    if cancelar_inicio:
        command.append('--cancelar-inicio')
    return subprocess.call(command, cwd=REPO, env=env)


def mark_lines(config,env,*,cancelar_inicio=False):
    """Solo líneas de dos puntos (sin zonas) sobre la fuente del YAML."""
    command = [sys.executable, str(REPO/'tools/cristhian/marcar_lineas.py'), '--config', str(config)]
    if cancelar_inicio:
        command.append('--cancelar-inicio')
    return subprocess.call(command, cwd=REPO, env=env)


def foreground(config,output,mark=None):
    """El detector libera la cámara antes del editor; después recarga su YAML.

    mark='zona' abre primero el editor de vía (4 esquinas, carriles con zona y línea) y mark='linea'
    el de líneas de dos puntos. Cancelar el marcado inicial detiene el arranque.
    """
    env=environment()
    if mark:
        editor = mark_lines if mark == 'linea' else edit_lanes
        result = editor(config, env, cancelar_inicio=True)
        if result == 130:
            print('Inicio cancelado durante la calibración.')
        if result:
            return result
    while True:
        result=subprocess.call(detector_command(config,output),cwd=REPO,env=env)
        if result!=20:return result
        result=edit_lanes(config,env)
        if result:return result
        # Guardar y cancelar vuelven al detector; cancelar conserva el YAML anterior.


VIDEO_EXT=('.mp4','.avi','.mov','.mkv','.m4v','.wmv')


def parse_source(text):
    """'0' -> cámara por índice, 'camara:Nombre' -> cámara por nombre, otra cosa -> archivo de video."""
    text=text.strip().strip('"').strip("'")
    if text.isdigit():return dict(tipo='camara',indice=int(text))
    if text.lower().startswith(('camara:','cámara:')):
        name=text.split(':',1)[1].strip()
        if not name:raise ValueError('Falta el nombre de la cámara después de camara:')
        return dict(tipo='camara',indice=0,nombre=name)
    path=Path(text).expanduser()
    if not path.is_file():raise ValueError(f'No existe el archivo de video: {text}')
    return dict(tipo='video',valor=str(path.resolve()).replace('\\','/'))


def list_camera_names(backend):
    """[(índice, nombre)] de las cámaras visibles; vacío si no se pueden enumerar."""
    try:
        import cv2
        sys.path.insert(0,str(REPO/'deteccion'))
        from cysa_detector.camera import list_cameras
        return [(c.index,c.name) for c in list_cameras(cv2,backend)]
    except Exception as error:
        print(f'No se pudieron listar las cámaras ({error}); se pedirá el índice.');return []


def pick_video_file():
    """Ventana para elegir el archivo; None si no hay entorno gráfico o se cancela."""
    try:
        import tkinter
        from tkinter import filedialog
        root=tkinter.Tk();root.withdraw();root.attributes('-topmost',True)
        path=filedialog.askopenfilename(title='Video para contar',filetypes=[('Video','*'+' *'.join(VIDEO_EXT)),('Todos','*.*')])
        root.destroy();return path or None
    except Exception:return None


def ask_source(settings,ask=input,cameras=None,pick_file=pick_video_file):
    """Menú de consola: cámara (lista por nombre) o archivo de video."""
    print('Fuente de detección:\n  1) Cámara\n  2) Archivo de video')
    while True:
        option=ask('Elegir 1 o 2: ').strip()
        if option in ('1','2'):break
    if option=='1':
        cameras=list_camera_names(settings.get('camera_backend','msmf')) if cameras is None else cameras
        if not cameras:return parse_source(ask('Índice de la cámara (0, 1...): '))
        for n,(index,name) in enumerate(cameras,1):print(f'  {n}) {name} (índice {index})')
        while True:
            value=ask('Número de la cámara: ').strip()
            if value.isdigit() and 1<=int(value)<=len(cameras):
                index,name=cameras[int(value)-1]
                same=[c for c in cameras if c[1].casefold()==name.casefold()]
                return dict(tipo='camara',indice=index,nombre=name if len(same)==1 else None)
    while True:
        path=pick_file() or ask('Ruta del video (puede arrastrar el archivo aquí): ')
        try:return parse_source(path)
        except ValueError as error:print(error)


def apply_source(settings,choice):
    """Copia del YAML con la fuente elegida y las opciones que corresponden a ese tipo de fuente."""
    s=deepcopy(settings)
    if choice['tipo']=='video':
        s['source']=choice['valor'];s.pop('camera_name',None)
        s['async_inference']=False;s['capture_latest']=False;s['ritmo_real']=True
    else:
        s['source']=choice['indice'];s['ritmo_real']=False
        if choice.get('nombre'):s['camera_name']=choice['nombre']
        else:s.pop('camera_name',None)
    return s


# Los perfiles exportados solo llevan opciones del detector. Las credenciales
# de MQTT se cargan por separado desde el archivo de entorno.
PROFILE_FIELDS = frozenset("""
    acceso_auto agnostic_nms async_inference auto_carriles calibracion_s
    camera_backend camera_fps camera_height camera_width capture_latest
    class_confidence class_map confidence conteo_reenlace_distancia
    conteo_reenlace_s crop_to_lanes device end2end imgsz intervalo_s iou
    lanes model prueba roi_padding show show_outside_lanes track_confidence tracker
""".split())
LANE_FIELDS = frozenset('acceso carril a b direction polygon'.split())


def clonar_perfil(settings, interseccion, choice):
    """Crea datos de configuración independientes para otra fuente o intersección."""
    if not isinstance(settings, dict):
        raise ValueError('El perfil base debe ser un mapa YAML')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', interseccion):
        raise ValueError('Intersección inválida: usar el ID del inventario')
    perfil = {key: value for key, value in settings.items() if key in PROFILE_FIELDS}
    if 'lanes' in perfil:
        lanes = perfil['lanes']
        if not isinstance(lanes, list) or any(not isinstance(lane, dict) for lane in lanes):
            raise ValueError('Los carriles del perfil deben ser una lista de mapas')
        perfil['lanes'] = [
            {key: value for key, value in lane.items() if key in LANE_FIELDS}
            for lane in lanes
        ]
    copia = apply_source(perfil, choice)
    copia.update(interseccion=interseccion, configuracion_verificada=False, auto_carriles=False)
    return copia


def guardar_perfil(args):
    import yaml

    base = yaml.safe_load(args.config.read_text(encoding='utf-8'))
    copia = clonar_perfil(base, args.interseccion, parse_source(args.fuente))
    contenido = yaml.safe_dump(copia, allow_unicode=True, sort_keys=False)
    # Abrir en modo exclusivo para proteger perfiles existentes incluso si se
    # lanzan dos clonaciones al mismo tiempo.
    archivo = args.salida.open('x', encoding='utf-8')
    try:
        with archivo:
            archivo.write(contenido)
    except OSError:
        args.salida.unlink(missing_ok=True)
        raise
    print(f'Perfil guardado en {args.salida}. Marca los carriles antes de iniciar.')
    return 0


def leer_perfil(config):
    import yaml

    perfil = yaml.safe_load(config.read_text(encoding='utf-8'))
    if not isinstance(perfil, dict):
        raise ValueError('El perfil debe ser un mapa YAML')
    return perfil


def session_config(config,choice,*,base=None):
    """YAML de sesión en resultados/detector/ (no modifica el perfil original).

    Devuelve (ruta, hay_que_marcar). Si la sesión anterior usó la misma fuente se conservan sus carriles;
    si la fuente cambió, los carriles del perfil pueden no servir y hay que marcarlos.
    """
    import yaml
    RUNTIME.mkdir(parents=True,exist_ok=True)
    path=RUNTIME/f'sesion_{config.stem}.yaml'
    if base is None:
        base = leer_perfil(config)
    settings=apply_source(base,choice)
    previous=yaml.safe_load(path.read_text(encoding='utf-8')) if path.exists() else None
    key=lambda c:(c.get('interseccion'),c.get('source'),c.get('camera_name'))
    if previous and key(previous)==key(settings):
        settings['lanes']=previous.get('lanes',settings.get('lanes'))
        settings['configuracion_verificada']=previous.get('configuracion_verificada',False)
        mark=not settings['configuracion_verificada']
    else:
        mark=key(settings)!=key(base) or not base.get('configuracion_verificada',False)
        if mark:settings['configuracion_verificada']=False
    path.write_text(yaml.safe_dump(settings,allow_unicode=True,sort_keys=False),encoding='utf-8')
    return path,mark


class FachadaConteo:
    """Coordina la fuente, el perfil, la calibración y el detector desde una sola entrada."""

    def iniciar(self, config, salida, *, fuente=None, marcar=None, segundo_plano=False):
        if running(load_state()):
            raise SystemExit('Ya hay un detector en segundo plano. Usa detener antes de iniciar otro.')
        if marcar and segundo_plano:
            raise SystemExit('--marcar necesita ventana: no usarlo con --segundo-plano')

        config = config.resolve()
        salida = salida.resolve()
        perfil = leer_perfil(config)
        try:
            if fuente is not None:
                choice = ask_source(perfil) if fuente == 'preguntar' else parse_source(fuente)
                config, necesita_marcar = session_config(config, choice, base=perfil)
                print(f'Configuración de esta sesión: {config}')
                if necesita_marcar and not marcar:
                    if segundo_plano:
                        raise SystemExit('Fuente nueva: marca los carriles primero (sin --segundo-plano)')
                    print('Fuente nueva: primero hay que marcar los carriles.')
                    marcar = 'zona'

            if segundo_plano:
                return iniciar_segundo_plano(config, salida)
            return foreground(config, salida, marcar)
        except KeyboardInterrupt:
            print('Sesión interrumpida.')
            return 130


def iniciar_segundo_plano(config,output):
    import yaml

    RUNTIME.mkdir(parents=True,exist_ok=True)
    lock=RUNTIME/'inicio.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise SystemExit('Hay otro inicio en curso; revisa resultados/detector/inicio.lock si quedó un cierre abrupto.')
    try:
        if running(load_state()):raise SystemExit('Ya hay un detector en segundo plano.')
        token=uuid4().hex
        runtime_config=RUNTIME/f'{token}.yaml'
        settings=leer_perfil(config);settings['show']=False
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
            result = process.poll()
            if result is not None:
                print(text[-3000:])
                return result
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
    a.add_argument('--fuente',nargs='?',const='preguntar',default=None,
                   help='Elegir la fuente al iniciar: sin valor muestra un menú; o 0/1 (índice), "camara:Nombre" o la ruta de un video')
    a.add_argument('--marcar',nargs='?',const='zona',choices=['zona','linea'],default=None,
                   help='Marcar antes de contar: zona (4 esquinas de la via, por defecto) o linea (2 puntos por carril)')
    a=sub.add_parser('clonar-perfil',help='Crear un YAML independiente pendiente de calibración')
    a.add_argument('--config',type=Path,required=True,help='Perfil base')
    a.add_argument('--interseccion',required=True,help='ID de destino en el inventario')
    a.add_argument('--fuente',required=True,help='Índice, camara:Nombre o archivo de video')
    a.add_argument('--salida',type=Path,required=True,help='Ruta del nuevo YAML')
    a=sub.add_parser('detener');a.add_argument('--espera',type=float,default=20)
    sub.add_parser('estado')
    a=sub.add_parser('_worker');a.add_argument('--config',type=Path,required=True);a.add_argument('--salida',type=Path,required=True)
    a.add_argument('--stop',type=Path,required=True);a.add_argument('--done',type=Path,required=True)
    args=p.parse_args()
    if args.action in {'iniciar', 'clonar-perfil'}:
        import yaml
        try:
            if args.action == 'clonar-perfil':
                return guardar_perfil(args)
            return FachadaConteo().iniciar(
                args.config, args.salida, fuente=args.fuente, marcar=args.marcar,
                segundo_plano=args.segundo_plano,
            )
        except (OSError, ValueError, yaml.YAMLError) as error:
            p.error(str(error))
    return stop(args) if args.action=='detener' else status() if args.action=='estado' else worker(args)

if __name__=='__main__':raise SystemExit(main())
