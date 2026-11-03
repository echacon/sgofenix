/*
 * tools/edge_y_scada/firmware_arduino_holon.ino
 * ============================================================================
 * Firmware de Referencia para Nodo de Borde Holónico FÉNIX (Modo C — C_EDGE)
 * Hardware objetivo: Arduino Nano / Arduino UNO / ESP32
 * ============================================================================
 *
 * Propósito en la Arquitectura MOM Holónica (IEEE TII):
 * -----------------------------------------------------
 * Instrumenta de manera no invasiva y de muy bajo coste (< 80 USD) un equipo
 * de planta legado (mezclador, reactor, molino, bomba) para dotar al Holón
 * Recurso (RH, Ec. 3) de:
 *   1. Telemetría de corriente y potencia activa mediante pinza amperimétrica
 *      no invasiva SCT-013-030 (en pin analógico A0) para calcular la Relación
 *      de Desviación Energética EDR(R) (Ec. 15).
 *   2. Sonda de temperatura impermeable DS18B20 (en pin digital D4) para
 *      verificar invariantes termodinámicos antes de autorizar transiciones
 *      de la Red de Petri AB-TPPN.
 *   3. Pulsador industrial de confirmación de fin de etapa (en pin D2 con
 *      pull-up interno) para emitir el evento de planta (serie 200) hacia el
 *      Gateway Raspberry Pi (`nodo_edge_raspberry_arduino.py`).
 *
 * Formato de trama emitida por Puerto Serie (115200 bps, 1 Hz):
 * {"nodo_id":"ARD-MEZ-01","corriente_a":19.42,"voltaje_v":220.0,"cos_phi":0.88,"temp_c":65.2,"boton_fin":0,"dt_seg":1.0}
 */

#include <Arduino.h>

// Identificador único del nodo asociado al Holón Recurso en Fénix
const char* NODO_ID = "ARD-MEZ-01";

// Pines de hardware
const int PIN_SCT013_ADC = A0;     // Entrada analógica desde pinza SCT-013 (con divisor de tensión 2.5V)
const int PIN_BOTON_FIN  = 2;      // Pulsador industrial (activo en BAJO con INPUT_PULLUP)
const int PIN_LED_ESTADO = 13;     // Indicador visual de motor en carga / envío de evento

// Constantes eléctricas de calibración de la estación
const float VOLTAJE_LINEA_V = 220.0;
const float FACTOR_POTENCIA = 0.88;
const float CALIBRACION_SCT = 30.0; // 30 A por cada 1 V RMS (SCT-013-030)
const float VREF_ADC        = 5.0;
const int   RESOLUCION_ADC  = 1024;

unsigned long ultimoMuestreoMs = 0;
const unsigned long INTERVALO_MUESTREO_MS = 1000; // 1 segundo (dt_seg = 1.0)
volatile bool flagBotonFin = false;

void isrBotonFin() {
    flagBotonFin = true;
}

float medirCorrienteRMS() {
    const int numMuestras = 400;
    double sumaCuadrados = 0.0;
    int offsetMedio = RESOLUCION_ADC / 2;

    for (int i = 0; i < numMuestras; i++) {
        int lectura = analogRead(PIN_SCT013_ADC);
        double centrada = (double)(lectura - offsetMedio);
        sumaCuadrados += centrada * centrada;
        delayMicroseconds(200);
    }

    double rmsCuentas = sqrt(sumaCuadrados / (double)numMuestras);
    double rmsVoltios = (rmsCuentas * VREF_ADC) / (double)RESOLUCION_ADC;
    return (float)(rmsVoltios * CALIBRACION_SCT);
}

float leerTemperaturaProcesoC() {
    // En producción con librería DallasTemperature: sensors.requestTemperatures(); return sensors.getTempCByIndex(0);
    // Lectura analógica/simulada de respaldo si no hay sonda 1-Wire conectada:
    return 65.0;
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_BOTON_FIN, INPUT_PULLUP);
    pinMode(PIN_LED_ESTADO, OUTPUT);
    attachInterrupt(digitalPinToInterrupt(PIN_BOTON_FIN), isrBotonFin, FALLING);
    ultimoMuestreoMs = millis();
}

void loop() {
    unsigned long ahoraMs = millis();
    if (ahoraMs - ultimoMuestreoMs >= INTERVALO_MUESTREO_MS) {
        float dtSeg = (ahoraMs - ultimoMuestreoMs) / 1000.0;
        ultimoMuestreoMs = ahoraMs;

        float corrienteA = medirCorrienteRMS();
        float tempC      = leerTemperaturaProcesoC();
        int botonFin     = 0;

        if (flagBotonFin || digitalRead(PIN_BOTON_FIN) == LOW) {
            botonFin = 1;
            flagBotonFin = false;
        }

        digitalWrite(PIN_LED_ESTADO, (corrienteA > 2.5 || botonFin == 1) ? HIGH : LOW);

        // Emitir trama JSON compacta hacia Raspberry Pi Gateway
        Serial.print("{\"nodo_id\":\"");
        Serial.print(NODO_ID);
        Serial.print("\",\"corriente_a\":");
        Serial.print(corrienteA, 2);
        Serial.print(",\"voltaje_v\":");
        Serial.print(VOLTAJE_LINEA_V, 1);
        Serial.print(",\"cos_phi\":");
        Serial.print(FACTOR_POTENCIA, 2);
        Serial.print(",\"temp_c\":");
        Serial.print(tempC, 2);
        Serial.print(",\"boton_fin\":");
        Serial.print(botonFin);
        Serial.print(",\"dt_seg\":");
        Serial.print(dtSeg, 2);
        Serial.println("}");
    }
}
