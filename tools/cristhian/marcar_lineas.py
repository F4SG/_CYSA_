"""Dibuja las líneas de conteo con clics y genera el bloque `lanes:` del YAML del detector.

Muestra la fuente en vivo en una ventana (solo RAM). No guarda cuadros, capturas ni video.
Uso:
    python tools/cristhian/marcar_lineas.py --source 0 --acceso N
    python tools/cristhian/marcar_lineas.py --source "C:/ruta/video.mp4" --acceso N   (el video se repite)
Clics: dos por carril (inicio a y fin b). Teclas: r = reiniciar, q = terminar e imprimir YAML.
Después copiar el bloque impreso a deteccion/config/carriles_<nombre>.yaml y revisar el sentido.
"""
import argparse


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


def main():
    import cv2
    p = argparse.ArgumentParser()
    p.add_argument('--source', default='0')
    p.add_argument('--acceso', default='N', help='ID del acceso, igual que en el inventario')
    p.add_argument('--alto', type=int, default=800, help='alto máximo de la ventana en píxeles')
    args = p.parse_args()
    source = int(args.source) if args.source.isdigit() else args.source
    es_archivo = isinstance(source, str)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit('No se pudo abrir la fuente. Probar antes con comprobar_camara.py')
    puntos = []

    def clic(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN:
            puntos.append((x, y))

    ventana = 'marcar lineas (no se guarda nada)'
    cv2.namedWindow(ventana)
    cv2.setMouseCallback(ventana, clic)
    try:
        while True:
            ok, frame = cap.read()
            if not ok and es_archivo:                       # video terminado: volver al inicio
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()
            if not ok:
                break
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
            if tecla == ord('r'):
                puntos.clear()
            if tecla == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    lineas = [((puntos[i][0] / w, puntos[i][1] / h), (puntos[i + 1][0] / w, puntos[i + 1][1] / h))
              for i in range(0, len(puntos) - 1, 2)]
    if not lineas:
        raise SystemExit('No se marcó ninguna línea')
    print(bloque_yaml(lineas, args.acceso))
    print('# Revisar: si los vehículos van en sentido contrario, usar positive_to_negative (o both).')


if __name__ == '__main__':
    main()
