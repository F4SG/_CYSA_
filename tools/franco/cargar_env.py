"""Ejecuta un proceso con un archivo .env sin imprimir sus valores."""
import argparse,os,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('env',type=Path);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    if not cmd:p.error('Falta comando después del archivo .env')
    # En Windows, 'python' dentro de un venv puede resolverse al Python del sistema (sin las librerías
    # del proyecto). Usar el mismo intérprete que ejecuta este script.
    if cmd[0] in ['python','python3']:cmd=[sys.executable]+cmd[1:]
    env=os.environ.copy()
    for line in a.env.read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            k,v=line.split('=',1);env[k.strip()]=v.strip()
    raise SystemExit(subprocess.call(cmd,env=env))
if __name__=='__main__':main()
