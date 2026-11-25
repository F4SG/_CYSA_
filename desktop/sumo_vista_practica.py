"""Prepara la vista de un lote de práctica ya medido en SUMO."""
from xml.etree.ElementTree import Element, SubElement, parse

from simulacion.sumo_base import write_xml


# La misma definición da color al vehículo y a su símbolo en la leyenda.
VEHICULOS = (
    ('auto', 'Auto', 'passenger/sedan', '68,199,255', ((-4, -1.5), (2, -1.5), (4, 0), (2, 1.5), (-4, 1.5))),
    ('micro', 'Micro', 'bus', '255,185,77', ((-5, -2), (5, -2), (5, 2), (-5, 2))),
    ('moto', 'Moto', 'motorcycle', '126,232,145', ((-3, -0.8), (1, -0.8), (3, 0), (1, 0.8), (-3, 0.8))),
)


def dibujar_entorno(carpeta, origen):
    entorno = Element('additional')
    cx, cy = origen

    def poligono(nombre, puntos, color, capa):
        forma = ' '.join(f'{cx + x:g},{cy + y:g}' for x, y in puntos)
        SubElement(entorno, 'poly', id=nombre, color=color, shape=forma, fill='true', layer=str(capa))

    def rectangulo(nombre, x1, y1, x2, y2, color, capa=-2):
        poligono(nombre, ((x1, y1), (x2, y1), (x2, y2), (x1, y2)), color, capa)

    def texto(nombre, etiqueta, x, y):
        SubElement(entorno, 'poi', id=nombre, type=etiqueta, color='0,0,0,0',
                   x=f'{cx + x:g}', y=f'{cy + y:g}')

    # Geometría decorativa fuera de la calzada. Los detectores siguen en el lote original.
    rectangulo('plaza', -107, 25, -23, 68, '47,76,67')
    rectangulo('sendero', -106, 43, -24, 46, '80,108,96', -1)
    arbol = ((-5, -2), (-2, -5), (2, -5), (5, -2), (5, 2), (2, 5), (-2, 5), (-5, 2))
    for indice, x in enumerate((-96, -78, -60, -42)):
        poligono(f'arbol_{indice}', ((x + dx, 34 + dy) for dx, dy in arbol), '66,101,81', -1)
    rectangulo('manzana_suroeste', -107, -64, -24, -25, '38,57,63')
    rectangulo('manzana_sureste', 23, -64, 109, -25, '38,57,63')
    for indice, (x, y) in enumerate(((-97, -54), (-62, -54), (32, -54), (69, -54))):
        rectangulo(f'techo_{indice}', x, y, x + 23, y + 19, '59,77,87', -1)

    rectangulo('tarjeta_leyenda', 26, 25, 105, 67, '17,30,42', 8)
    rectangulo('borde_leyenda', 26, 66, 105, 67, '112,147,170', 9)
    texto('titulo_leyenda', 'Vehículos', 66, 62)
    for fila, (clase, etiqueta, _, color, puntos) in enumerate(VEHICULOS):
        y = 51 - 9 * fila
        poligono(f'simbolo_{clase}', ((40 + x, y + dy) for x, dy in puntos), color, 9)
        texto(f'etiqueta_{clase}', etiqueta, 69, y + 4)

    for acceso, x, y in (('Norte', -16, 76), ('Sur', -17, -66), ('Este', 88, -11), ('Oeste', -88, 15)):
        texto(f'acceso_{acceso}', acceso, x, y)
    texto('titulo_cruce', 'DEMO_INT_01', -64, 56)
    write_xml(carpeta / 'entorno-practica.add.xml', entorno)


def preparar_vista(config_original):
    carpeta = config_original.parent
    config = parse(config_original).getroot()
    entrada = config.find('input')
    red = parse(carpeta / entrada.find('net-file').attrib['value']).getroot()
    cruce = red.find("junction[@id='C']")
    x, y = (float(cruce.attrib[eje]) for eje in ('x', 'y'))
    dibujar_entorno(carpeta, (x, y))

    archivo_rutas = entrada.find('route-files')
    rutas = parse(carpeta / archivo_rutas.attrib['value']).getroot()
    for clase, _, figura, color, _ in VEHICULOS:
        tipo = rutas.find(f"vType[@id='{clase}']")
        tipo.set('guiShape', figura)
        tipo.set('color', color)
    write_xml(carpeta / 'flujos-visual.rou.xml', rutas)
    archivo_rutas.set('value', 'flujos-visual.rou.xml')
    adicionales = entrada.find('additional-files')
    adicionales.set('value', adicionales.attrib['value'] + ',entorno-practica.add.xml')

    vista = Element('viewsettings')
    esquema = SubElement(vista, 'scheme', name='real world')
    SubElement(esquema, 'background', backgroundColor='26,47,52', showGrid='false')
    for elemento, entrada_color in (('edges', 'road'), ('junctions', '')):
        parte = SubElement(esquema, elemento)
        colores = SubElement(parte, 'colorScheme', name='uniform')
        SubElement(colores, 'entry', name=entrada_color, color='53,59,69')
    SubElement(esquema, 'vehicles', vehicleMode='3', vehicleQuality='2',
               vehicle_minSize='0', vehicle_exaggeration='1.65', scaleLength='true')
    SubElement(esquema, 'pois', poiType_show='true', poiType_size='65', poiType_constantSize='true',
               poiType_color='235,244,250', poiType_bgColor='0,0,0,0')
    SubElement(vista, 'viewport', zoom='345', x=str(x), y=str(y + 3), angle='0')
    write_xml(carpeta / 'vista-practica.xml', vista)

    SubElement(SubElement(config, 'gui_only'), 'gui-settings-file', value='vista-practica.xml')
    SubElement(SubElement(config, 'output'), 'output-prefix', value='reproduccion-')
    visual = carpeta / 'practica-visual.sumocfg'
    write_xml(visual, config)
    return visual
