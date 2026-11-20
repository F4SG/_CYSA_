"""Crea una clave por instalación, sin reemplazarla ni imprimir secretos."""
import argparse,os,secrets
from pathlib import Path

def preparar(repo):
    target=Path(repo)/'infra/runtime/control/clave.key';target.parent.mkdir(parents=True,exist_ok=True)
    try:fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        if len(target.read_bytes())!=32:raise ValueError('Clave existente inválida: revisar antes de continuar')
        return target
    with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32))
    return target
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2]);a=p.parse_args()
    print('Clave del banco preparada en',preparar(a.repo),'; no se sobrescriben claves existentes.')
