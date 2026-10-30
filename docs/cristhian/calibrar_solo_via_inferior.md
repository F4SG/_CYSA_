# Calibrar únicamente la vía inferior

En la toma del celular hay vías en distintos planos. La heurística de trayectorias activó una sola zona
estrecha a partir de un grupo parcial y dejó vehículos de otros recorridos fuera. Para esta prueba no se
acepta esa propuesta como una calibración válida ni se declara cumplida la precisión RF-03.

El perfil del S10+ queda con auto_carriles=false, configuracion_verificada=false y sin líneas inventadas.
Se conserva el perfil rápido de YOLO26, la cámara por nombre y los contratos de conteo. El detector no
arranca hasta guardar una geometría revisada. Un proceso antiguo debe cerrarse con Q para cargar cambios.

```powershell
Set-Location "$env:USERPROFILE\Documents\CYSA_S1\repo_s1"
.\.venv\Scripts\python.exe tools/cristhian/calibrar_via.py --iniciar
```

Con el teléfono fijo, esperar a que aparezca video y pulsar **Espacio** para fijar la imagen en RAM.
La cámara permanece abierta incluso durante el marcado; el cuadro negro de arranque no puede fijarse.
Pulsar Espacio de nuevo reanuda la vista y borra las marcas pendientes. Después marcar en este orden:

1. Esquina lejana izquierda de la vía inferior.
2. Esquina lejana derecha de la misma vía.
3. Esquina cercana derecha.
4. Esquina cercana izquierda.

Elegir un tramo de asfalto que contenga únicamente los carriles de la vía inferior. Excluir vereda,
separador, puente y controles del reproductor. La herramienta proyecta divisiones de ancho uniforme
en un rectángulo de referencia a través de una homografía. Esto es una propuesta geométrica,
no reconocimiento automático de marcas viales. Revisar que las divisiones sigan las líneas reales.
Si hay carriles de anchos diferentes, curvas o una propuesta que no encaja, cancelar y usar
`delimitar_carriles.py` para dibujar cada carril de forma independiente.

Las teclas 1–8 eligen la cantidad correcta; tres es solo la propuesta inicial. U deshace una esquina.
+/- mueve las líneas de conteo dentro de la zona. S guarda y, con --iniciar, abre el detector al liberar
la cámara del marcador. Q/Esc cancela sin guardar. Por defecto cuenta del borde lejano al cercano;
--direction positive_to_negative invierte el sentido y --direction both acepta ambos.

Al guardar se crean IDs estables N_0, N_1..., líneas y polígonos fijos; se pone
configuracion_verificada=true, show=true y show_outside_lanes=false. Los vehículos del puente
quedan fuera de los polígonos, por lo que no se dibujan ni cuentan. El modelo todavía procesa la
imagen de cámara completa, sin añadir una fuente de detección ni un modelo distinto.

Si se mueve el teléfono o el encuadre, repetir esta calibración. R solo reinicia el modo automático
cuando está habilitado; no debe usarse para sustituir las zonas fijas de esta prueba. El conteo formal
requiere comparar auto/micro/moto por carril y sentido con una muestra manual y diferencia ≤10 %.
La geometría no se copió de una captura de escritorio porque no garantiza las coordenadas actuales
que realmente entrega el S10+. No se guardaron cuadros ni videos durante la preparación de la herramienta.

Corrección de captura: el calibrador anterior leía un único cuadro y liberaba la cámara antes del marcado.
Eso podía fijar negro de arranque y apagar la conexión virtual. Ahora lee durante toda la sesión, espera
imagen no uniforme y solo libera al guardar, cancelar o fallar. La comprobación de imagen útil no acredita
enfoque ni precisión óptica. Se prueba la secuencia negro→video→Espacio→marcar→guardar, sin cámara real;
queda pendiente repetirla con el S10+ de la sesión del usuario.
