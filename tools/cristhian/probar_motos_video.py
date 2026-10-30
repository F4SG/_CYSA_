"""Comprueba detección y seguimiento en un video externo, sin MQTT, CSV ni guardar imágenes."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'deteccion'))
from cysa_detector.inference import detection_settings

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--video',type=Path,required=True)
    p.add_argument('--config',type=Path,default=ROOT/'deteccion/config/carriles_cristhian.yaml')
    p.add_argument('--desde',type=float,default=0,help='Segundo de inicio del archivo')
    args=p.parse_args()
    if args.desde<0:p.error('--desde debe ser positivo o cero')
    import cv2,yaml
    from ultralytics import YOLO
    config=yaml.safe_load(args.config.read_text(encoding='utf-8'))
    mapping={int(k):v for k,v in config['class_map'].items()}
    options,thresholds=detection_settings(config,mapping)
    model_path=Path(config.get('model','yolo26n.pt'))
    if not model_path.is_absolute():model_path=ROOT/model_path
    model=YOLO(str(model_path))
    cap=cv2.VideoCapture(str(args.video))
    if not cap.isOpened():raise SystemExit('No se pudo abrir el archivo de video')
    cap.set(cv2.CAP_PROP_POS_MSEC,args.desde*1000)
    window='CYSA - Prueba de motos en video | Q: salir'
    cv2.namedWindow(window,cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(window,900,800)
    print('Prueba visual: sin publicar conteos ni guardar cuadros. La velocidad depende de la CPU.',flush=True)
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            seconds=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
            results=model.track(frame,**options)
            boxes=results[0].boxes;motos=0
            if boxes is not None:
                ids=boxes.id.int().cpu().tolist() if boxes.id is not None else [None]*len(boxes)
                for xyxy,cls,score,tid in zip(boxes.xyxy.cpu().tolist(),boxes.cls.int().cpu().tolist(),boxes.conf.cpu().tolist(),ids):
                    if score<thresholds.get(cls,1):continue
                    x1,y1,x2,y2=map(int,xyxy);color=(0,220,255) if cls==3 else (160,160,160)
                    cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
                    identity=f'#{tid}' if tid is not None else 'sin ID'
                    cv2.putText(frame,f'{mapping.get(cls,"vehiculo")} {identity} {score:.2f}',(x1,max(18,y1-6)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
                    if cls==3:motos+=1
            cv2.rectangle(frame,(0,0),(frame.shape[1],38),(0,0,0),-1)
            cv2.putText(frame,f'{seconds:.1f}s | motos visibles: {motos} | sin conteo | Q: salir',(10,26),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1)
            cv2.imshow(window,frame)
            key=cv2.waitKey(1)&255
            if key in (ord('q'),27) or cv2.getWindowProperty(window,cv2.WND_PROP_VISIBLE)<1:break
    finally:cap.release();cv2.destroyAllWindows()

if __name__=='__main__':main()
