"""Lista nombres e índices por backend; no abre las cámaras ni guarda cuadros."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'deteccion'))
from cysa_detector.camera import list_cameras

def main():
    import cv2
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend',choices=['auto','msmf','dshow'],default='msmf')
    args=p.parse_args()
    cameras=list_cameras(cv2,args.backend)
    for camera in cameras:print(f'{camera.index}: {camera.name} (backend {camera.backend})')
    if not cameras:raise SystemExit('No hay cámaras accesibles desde esta sesión')

if __name__=='__main__':main()
