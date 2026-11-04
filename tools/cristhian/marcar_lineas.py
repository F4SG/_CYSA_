"""Dibuja las líneas de conteo con clics y genera el bloque `lanes:` del YAML del detector.

Muestra la fuente en vivo en una ventana (solo RAM). No guarda cuadros, capturas ni video.
Uso:
    python tools/cristhian/marcar_lineas.py --source 0 --acceso N
    python tools/cristhian/marcar_lineas.py --source "C:/ruta/video.mp4" --acceso N   (el video se repite)
    python tools/cristhian/marcar_lineas.py --config deteccion/config/video_santa_cruz.yaml
        usa la fuente del YAML y, al terminar, guarda las líneas en ese YAML (sin zonas)
Clics: dos por carril (inicio a y fin b). Teclas: ESPACIO = pausar/seguir, r = reiniciar,
q = terminar (imprime o guarda), Esc = cancelar sin guardar.
Sin --config, copiar el bloque impreso a deteccion/config/carriles_<nombre>.yaml y revisar el sentido.
"""
import argparse
from pathlib import Path


def sentido_positivo(a, b):
    """Hacia dónde se mueve un vehículo que cruza de lado negativo a positivo (coordenadas de imagen)."""
    nx, ny = -(b[1] - a[1]), b[0] - a[0]          # normal que apunta al lado positivo de cross(a, b, p)
    if abs(ny) >= abs(nx):
        return 'hacia abajo' if ny > 0 else 'hacia arriba'
    return 'hacia la derecha' if nx > 0 else 'hacia la izquierda'


def bloque_yaml(lineas, acceso):
    """lineas: lista de (a, b) normalizados. Devuelve el texto YAML de `lanes:`."""
    salida = ['lanes:']
    for i, (a, b) in enumerate(lineas):
        salida += [f'  - acceso: {acceso}',
                   f'    carril: {acceso}_{i}',
                   f'    a: [{a[0]:.3f}, {a[1]:.3f}]',
                   f'    b: [{b[0]:.3f}, {b[1]:.3f}]',
                   f'    direction: negative_to_positive  # cuenta vehículos que se mueven {sentido_positivo(a, b)}']
    return '\n'.join(salida)


def guardar(ruta, lineas, acceso, direction='negative_to_positive'):
    """Escribe las líneas (sin zonas) en el YAML del detector y lo marca como verificado."""
    import yaml
    config = yaml.safe_load(Path(ruta).read_text(encoding='utf-8'))
    config.update(lanes=[dict(acceso=acceso, carril=f'{acceso}_{i}', a=[round(v, 4) for v in a],
                              b=[round(v, 4) for v in b], direction=direction) for i, (a, b) in enumerate(lineas)],
                  configuracion_verificada=True, auto_carriles=False, crop_to_lanes=False)
    Path(ruta).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return config


def main():
    import cv2
    p = argparse.ArgumentParser()
    p.add_argument('--source', default='0')
    p.add_argument('--config', type=Path, help='leer la fuente de este YAML y guardar ahí las líneas')
    p.add_argument('--acceso', default=None, help='ID del acceso, igual que en el inventario')
    p.add_argument('--direction', default='negative_to_positive',
                   choices=['negative_to_positive', 'positive_to_negative', 'both'])
    p.add_argument('--alto', type=int, default=800, help='alto máximo de la ventana en píxeles')
    args = p.parse_args()
    if args.config:
        import sys
        import yaml
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'deteccion'))
        from cysa_detector.camera import open_source
        config = yaml.safe_load(args.config.read_text(encoding='utf-8'))
        source = config.get('source', 0)
        lanes = config.get('lanes') or []
        args.acceso = args.acceso or (lanes[0].get('acceso') if lanes else 'N')
        cap = open_source(cv2, source, {k: v for k, v in config.items() if k != 'capture_latest'})
    else:
        source = int(args.source) if args.source.isdigit() else args.source
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise SystemExit('No se pudo abrir la fuente. Probar antes con comprobar_camara.py')
    args.acceso = args.acceso or 'N'
    es_archivo = isinstance(source, str)
    puntos = []
    pausa, frame_fijo, cancelado = False, None, False

    def clic(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN:
            puntos.append((x, y))

    ventana = 'marcar lineas (no se guardan imagenes)'
    cv2.namedWindow(ventana)
    cv2.setMouseCallback(ventana, clic)
    try:
        while True:
            if pausa and frame_fijo is not None:
                ok, frame = True, frame_fijo.copy()
            else:
                ok, frame = cap.read()
                if not ok and es_archivo:                   # video terminado: volver al inicio
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok, frame = cap.read()
                if not ok:
                    break
                frame_fijo = frame.copy()
            escala = min(1.0, args.alto / frame.shape[0])   # videos verticales o 4K caben en pantalla
            if escala < 1.0:
                frame = cv2.resize(frame, None, fx=escala, fy=escala)
            h, w = frame.shape[:2]                           # los clics se miden sobre la ventana mostrada
            for x, y in puntos:
                cv2.circle(frame, (x, y), 5, (0, 255, 255), -1)
            for i in range(0, len(puntos) - 1, 2):
                cv2.line(frame, puntos[i], puntos[i + 1], (0, 255, 255), 2)
                cv2.putText(frame, f'{args.acceso}_{i // 2}', puntos[i], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.imshow(ventana, frame)
            del frame
            tecla = cv2.waitKey(30) & 0xFF
            if tecla == ord(' '):
                pausa = not pausa
            if tecla == ord('r'):
                puntos.clear()
            if tecla == ord('q'):
                break
            if tecla == 27 or cv2.getWindowProperty(ventana, cv2.WND_PROP_VISIBLE) < 1:
                cancelado = True
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        frame_fijo = None
    if cancelado:
        print('Cancelado: configuracion sin cambios.')
        return
    lineas = [((puntos[i][0] / w, puntos[i][1] / h), (puntos[i + 1][0] / w, puntos[i + 1][1] / h))
              for i in range(0, len(puntos) - 1, 2)]
    if not lineas:
        raise SystemExit('No se marcó ninguna línea')
    if args.config:
        guardar(args.config, lineas, args.acceso, args.direction)
        print(f'Guardadas {len(lineas)} lineas en {args.config} (sentido {args.direction}).')
        for a, b in lineas:
            print(f'  cuenta vehiculos que se mueven {sentido_positivo(a, b)} al cruzar')
        return
    print(bloque_yaml(lineas, args.acceso))
    print('# Revisar: si los vehículos van en sentido contrario, usar positive_to_negative (o both).')


if __name__ == '__main__':
    main()
