"""Vista en directo y resolución efectivamente recibida. No guarda imágenes."""
import argparse,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'deteccion'))
from cysa_detector.camera import open_source

def main():
    import cv2
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=int,default=1)
    p.add_argument('--name',help='Nombre exacto o fragmento unico; tiene prioridad sobre --source')
    p.add_argument('--width',type=int,default=1920)
    p.add_argument('--height',type=int,default=1080)
    p.add_argument('--fps',type=int,default=30)
    p.add_argument('--backend',choices=['auto','msmf','dshow'],default='msmf')
    a=p.parse_args()
    config=dict(camera_width=a.width,camera_height=a.height,camera_fps=a.fps,camera_backend=a.backend)
    if a.name:config['camera_name']=a.name
    cap=open_source(cv2,a.source,config)
    window='Prueba de calidad - Q: salir';start=time.monotonic();last_size=None
    cv2.namedWindow(window,cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(window,960,540)
    print(f'Solicitado: {a.width}x{a.height} a {a.fps} fps. Esperando imagen...',flush=True)
    try:
        while True:
            ok,frame=cap.read()
            if ok:
                h,w=frame.shape[:2]
                if (w,h)!=last_size:
                    print(f'RECIBIDO REAL: {w}x{h}. FPS informado por el controlador: {cap.get(cv2.CAP_PROP_FPS):.1f}',flush=True)
                    if (w,h)!=(a.width,a.height):print('El controlador no entrego la resolucion solicitada; no se ampliara artificialmente.',flush=True)
                    last_size=(w,h)
                start=time.monotonic()
                cv2.rectangle(frame,(0,0),(min(w,1100),36),(0,0,0),-1)
                cv2.putText(frame,f'{a.name or ("Fuente "+str(a.source))} | Real: {w}x{h} | Q: salir',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),1)
                cv2.imshow(window,frame)
            elif time.monotonic()-start>15:raise SystemExit('No se recibio imagen durante 15 segundos')
            key=cv2.waitKey(20)&255
            if key in (ord('q'),27) or cv2.getWindowProperty(window,cv2.WND_PROP_VISIBLE)<1:break
    finally:cap.release();cv2.destroyAllWindows()

if __name__=='__main__':main()
