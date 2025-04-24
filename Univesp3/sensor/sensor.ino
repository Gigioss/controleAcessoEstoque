#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Casa_1G";
const char* password = "1qaz2wsx3edc";
const char* serverUrl = "http://192.168.1.2:5000/api/registro-bidirecional";

const byte sensorEntrada = 34;  // Sensor externo (entrada)
const byte sensorSaida = 35;    // Sensor interno (saída)
const byte pinoLed = 2;

bool ultimoEstadoEntrada = false;
bool ultimoEstadoSaida = false;
unsigned long ultimaAtivacao = 0;
const unsigned long debounceTime = 500; // ms

void setup() {
  Serial.begin(115200);
  pinMode(sensorEntrada, INPUT);
  pinMode(sensorSaida, INPUT);
  pinMode(pinoLed, OUTPUT);
  
  conectarWiFi();
}

void loop() {
  bool estadoAtualEntrada = digitalRead(sensorEntrada);
  bool estadoAtualSaida = digitalRead(sensorSaida);
  unsigned long tempoAtual = millis();

  // Lógica de detecção de entrada (34 -> 35)
  if (estadoAtualEntrada && !ultimoEstadoEntrada && 
      tempoAtual - ultimaAtivacao > debounceTime) {
    delay(50); // Debounce adicional
    if (digitalRead(sensorSaida)) {
      Serial.println("Sequência ENTRADA detectada (34->35)");
      enviarEvento("entrada");
      ultimaAtivacao = tempoAtual;
    }
  }

  // Lógica de detecção de saída (35 -> 34)
  if (estadoAtualSaida && !ultimoEstadoSaida && 
      tempoAtual - ultimaAtivacao > debounceTime) {
    delay(50); // Debounce adicional
    if (digitalRead(sensorEntrada)) {
      Serial.println("Sequência SAÍDA detectada (35->34)");
      enviarEvento("saida");
      ultimaAtivacao = tempoAtual;
    }
  }

  ultimoEstadoEntrada = estadoAtualEntrada;
  ultimoEstadoSaida = estadoAtualSaida;
  delay(10);
}

void enviarEvento(String tipo) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi não conectado");
    return;
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  
  String payload = "{\"tipo\":\"" + tipo + "\"}";
  int httpCode = http.POST(payload);

  if (httpCode == HTTP_CODE_OK) {
    String resposta = http.getString();
    Serial.println("Resposta: " + resposta);
    piscarLed(2); // Confirmação visual
  } else {
    Serial.println("Erro na requisição: " + String(httpCode));
  }
  http.end();
}

void piscarLed(int vezes) {
  for(int i=0; i<vezes; i++) {
    digitalWrite(pinoLed, HIGH);
    delay(200);
    digitalWrite(pinoLed, LOW);
    delay(200);
  }
}

void conectarWiFi() {
  Serial.println("\nConectando-se ao WiFi...");
  
  WiFi.disconnect(true);
  delay(100);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  unsigned long inicio = millis();
  bool conectado = false;
  
  while (millis() - inicio < 20000) { // Timeout de 20 segundos
    if (WiFi.status() == WL_CONNECTED) {
      conectado = true;
      break;
    }
    Serial.print(".");
    delay(500);
  }

  if (conectado) {
    Serial.println("\nWiFi conectado com sucesso!");
    Serial.print("Endereco IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(pinoLed, HIGH);
    
    // Inicia detecção automaticamente após conexão
    sistemaPronto = true;
    Serial.println("Sistema de deteccao iniciado automaticamente");
  } else {
    Serial.println("\nFalha na conexao WiFi");
    Serial.println("Reinicie o dispositivo para tentar novamente");
    digitalWrite(pinoLed, LOW);
    while(true); // Trava o sistema
  }
}