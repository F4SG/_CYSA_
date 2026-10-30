import argparse,json,platform,socket,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('resultados/diagnostico.json'));a=p.parse_args()
    root=Path(__file__).resolve().parents[2];checks=[]
    for command in [['docker','version','--format','{{.Server.Version}}'],['docker','compose','version'],['wsl','--version']]:
        try:r=subprocess.run(command,capture_output=True,text=True,timeout=20);ok=r.returncode==0;detail=r.stdout.strip()[:400] if ok else 'No disponible o no iniciado'
        except (OSError,subprocess.TimeoutExpired):ok=False;detail='No disponible'
        checks.append({'comando':' '.join(command),'ok':ok,'detalle':detail})
    for path in ['shared/cysa/contracts.py','backend/app/main.py','inventario/cysa_inventory/router.py','panel/index.html','identidad/realm.template.json','infra/compose.yaml','simulacion/sumo_base.py']:
        checks.append({'archivo':path,'ok':(root/path).is_file()})
    ports={}
    for port in [8080,8088,8883,8766]:
        with socket.socket() as s:s.settimeout(.3);ports[str(port)]='ocupado' if s.connect_ex(('127.0.0.1',port))==0 else 'libre'
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps({'python':platform.python_version(),'arquitectura':platform.machine(),'checks':checks,'puertos_loopback':ports,
      'nota':'No lee ni exporta archivos de credenciales. Puerto ocupado es normal si el servicio ya está activo.'},indent=2,ensure_ascii=False),encoding='utf-8')
    print('Diagnóstico guardado en',a.out)
if __name__=='__main__':main()
