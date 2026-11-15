// Monitor de conflictos (MMU) del banco de pruebas - Sistema IoT de Gestión Semafórica Adaptativa.
//
// La PC (cysa_controlador) decide las fases y envía las luces por USB-serial. Esta placa:
//   1. enciende los LEDs de cada grupo;
//   2. verifica las reglas de seguridad y, si alguna se rompe, pone todo en ROJO INTERMITENTE
//      y deja de obedecer a la PC hasta que se presione RESET (como un MMU real).
//
// Protocolo (115200 baudios, una línea por mensaje):
//   PC -> placa : L:<luces>   una letra por grupo, G verde, Y ámbar, R rojo. Ej.: L:GR
//   placa -> PC : LISTO:<n>   al encender
//                 FALLA:<motivo>  CONFLICTO, SIN_AMBAR, AMBAR_CORTO, AMBAR_A_VERDE, FORMATO, SIN_SENAL
//
// Funciona en Arduino Uno, Nano y Mega. AJUSTAR la sección CONFIGURACIÓN al montaje real.

// ======================= CONFIGURACIÓN =======================
const uint8_t N_GRUPOS = 2;                       // mismo orden que "grupos" del YAML: NS, EO
const uint8_t PIN_ROJO[N_GRUPOS]  = {2, 5};
const uint8_t PIN_AMBAR[N_GRUPOS] = {3, 6};
const uint8_t PIN_VERDE[N_GRUPOS] = {4, 7};
// true si los dos grupos no pueden tener paso (verde o ámbar) al mismo tiempo
const bool CONFLICTO[N_GRUPOS][N_GRUPOS] = {
  {false, true},
  {true,  false},
};
const unsigned long AMBAR_MIN_MS = 2800;          // ámbar mínimo del YAML (3 s) menos 0,2 s de tolerancia
const unsigned long WATCHDOG_MS = 1000;           // sin mensajes de la PC por más de 1 s -> falla
const unsigned long PARPADEO_MS = 500;
const uint8_t PIN_ESTADO = LED_BUILTIN;           // encendido = falla
// =============================================================

char actual[N_GRUPOS];
unsigned long desdeAmbar[N_GRUPOS];
unsigned long ultimoMensaje = 0;
bool armado = false;                              // el watchdog se activa con el primer mensaje válido
bool falla = false;
const char *motivo = "";
char linea[24];
uint8_t largo = 0;

void encender(uint8_t g, char luz) {
  digitalWrite(PIN_ROJO[g],  luz == 'R' ? HIGH : LOW);
  digitalWrite(PIN_AMBAR[g], luz == 'Y' ? HIGH : LOW);
  digitalWrite(PIN_VERDE[g], luz == 'G' ? HIGH : LOW);
}

void entrarFalla(const char *m) {
  if (falla) return;
  falla = true;
  motivo = m;
  digitalWrite(PIN_ESTADO, HIGH);
  Serial.print("FALLA:");
  Serial.println(motivo);
}

void procesar() {
  if (falla) {                                    // recordar la falla a la PC
    Serial.print("FALLA:");
    Serial.println(motivo);
    return;
  }
  if (largo != 2 + N_GRUPOS || linea[0] != 'L' || linea[1] != ':') { entrarFalla("FORMATO"); return; }
  char nuevo[N_GRUPOS];
  for (uint8_t g = 0; g < N_GRUPOS; g++) {
    nuevo[g] = linea[2 + g];
    if (nuevo[g] != 'G' && nuevo[g] != 'Y' && nuevo[g] != 'R') { entrarFalla("FORMATO"); return; }
  }
  for (uint8_t a = 0; a < N_GRUPOS; a++)
    for (uint8_t b = a + 1; b < N_GRUPOS; b++)
      if (CONFLICTO[a][b] && nuevo[a] != 'R' && nuevo[b] != 'R') { entrarFalla("CONFLICTO"); return; }
  unsigned long ahora = millis();
  for (uint8_t g = 0; g < N_GRUPOS; g++) {
    if (actual[g] == 'G' && nuevo[g] == 'R') { entrarFalla("SIN_AMBAR"); return; }
    if (actual[g] == 'Y' && nuevo[g] == 'G') { entrarFalla("AMBAR_A_VERDE"); return; }
    if (actual[g] == 'Y' && nuevo[g] == 'R' && ahora - desdeAmbar[g] < AMBAR_MIN_MS) { entrarFalla("AMBAR_CORTO"); return; }
  }
  for (uint8_t g = 0; g < N_GRUPOS; g++) {
    if (nuevo[g] == 'Y' && actual[g] != 'Y') desdeAmbar[g] = ahora;
    actual[g] = nuevo[g];
    encender(g, actual[g]);
  }
  ultimoMensaje = ahora;
  armado = true;
}

void setup() {
  for (uint8_t g = 0; g < N_GRUPOS; g++) {
    pinMode(PIN_ROJO[g], OUTPUT);
    pinMode(PIN_AMBAR[g], OUTPUT);
    pinMode(PIN_VERDE[g], OUTPUT);
    actual[g] = 'R';
    encender(g, 'R');                             // arranca en todo rojo
  }
  pinMode(PIN_ESTADO, OUTPUT);
  digitalWrite(PIN_ESTADO, LOW);
  Serial.begin(115200);
  Serial.print("LISTO:");
  Serial.println(N_GRUPOS);
}

void loop() {
  while (Serial.available() > 0) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      linea[largo] = '\0';
      if (largo > 0) procesar();
      largo = 0;
    } else if (largo < sizeof(linea) - 1) {
      linea[largo++] = ch;
    } else {
      largo = 0;
      entrarFalla("FORMATO");
    }
  }
  if (!falla && armado && millis() - ultimoMensaje > WATCHDOG_MS) entrarFalla("SIN_SENAL");
  if (falla) {                                    // rojo intermitente en todos los grupos
    bool prendido = (millis() / PARPADEO_MS) % 2 == 0;
    for (uint8_t g = 0; g < N_GRUPOS; g++) {
      digitalWrite(PIN_VERDE[g], LOW);
      digitalWrite(PIN_AMBAR[g], LOW);
      digitalWrite(PIN_ROJO[g], prendido ? HIGH : LOW);
    }
  }
}
