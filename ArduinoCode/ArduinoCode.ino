// Pin untuk kontrol motor
const int IN1 = 8;   
const int IN2 = 9;   
const int ENA = 10;  

// Pin untuk encoder
const int encoderPinA = 2; 

// Variabel untuk encoder
volatile int encoderCount = 0; 
unsigned long lastTime = 0;    
int rpm = 0;                   

// Penyesuaian pwm dengan gearbox
float gearRatio = 9.6;
int rpmValue = 0;            
const int maxRPM = 620;        
const int maxPWM = 255;        

// PID Variables
float kp = 0;     
float ki = 0;     
float kd = 0;     

float setpoint = 0; 
float Error = 0, prevError = 0, integralError = 0, derivativeError = 0;
int pidValue = 0;  

void setup() {
    Serial.begin(9600); 
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(ENA, OUTPUT);
    pinMode(encoderPinA, INPUT);

    attachInterrupt(digitalPinToInterrupt(encoderPinA), countEncoder, RISING);
}

void loop() {
    unsigned long currentTime = millis();

    // Hitung kecepatan motor setiap 100 ms
    if (currentTime - lastTime >= 100) {
        readSensor();
        pidValue = PIDControl();
        analogWrite(ENA, pidValue);
        sendToGUI();
        lastTime = currentTime;
    }

    // Cek perintah dari Serial Monitor
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n'); // Baca input hingga '\n'
        handleCommand(command); // Proses perintah
    }
}

// Fungsi interrupt untuk menghitung pulse encoder
void countEncoder() {
    encoderCount++;
}

// Fungsi untuk menghitung RPM berdasarkan pulse encoder
float readSensor() {
    rpm = (encoderCount / 11.0) * 600; // Disesuaikan dengan interval 100 ms
    rpmValue = rpm / gearRatio;       
    encoderCount = 0;                 
    return rpmValue;
}

// Fungsi untuk mengatur kecepatan motor menggunakan PID
int PIDControl() {
    float PControl, IControl, DControl; 
    Error = setpoint - rpmValue;
    PControl = kp * Error;
    integralError += Error;
    IControl = ki * integralError;
    DControl = kd * derivativeError;
    derivativeError = Error - prevError;
    prevError = Error;
    pidValue = constrain(PControl + IControl + DControl, 0, maxPWM);
    return pidValue;
}

// Fungsi untuk mengirim data ke GUI
void sendToGUI() {
    Serial.print("RPM:"); 
    Serial.println(rpmValue);
    Serial.print("Error:"); 
    Serial.println(Error);
}

// Fungsi untuk menangani perintah dari GUI
void handleCommand(String command) {
    int delimiterIndex = command.indexOf(':');
    if (delimiterIndex > 0) {
        String param = command.substring(0, delimiterIndex);
        String value = command.substring(delimiterIndex + 1);

        if (param == "Kp ") {
            kp = value.toFloat();
            Serial.println("Kp updated: " + String(kp));
        } else if (param == "Ki ") {
            ki = value.toFloat();
            Serial.println("Ki updated: " + String(ki));
        } else if (param == "Kd ") {
            kd = value.toFloat();
            Serial.println("Kd updated: " + String(kd));
        } else if (param == "RPM") {
            setpoint = value.toInt();
            Serial.println("Target RPM updated: " + String(setpoint));
        } else if (param == "DIR") {
            if (value == "CW") {
                setMotorDirection(true);
                Serial.println("Direction set to CW");
            } else if (value == "CCW") {
                setMotorDirection(false);
                Serial.println("Direction set to CCW");
            } else if (value == "S") {
                stopMotor(); 
                Serial.println("Motor stopped");
            }
        }
    }
}

// Fungsi untuk mengatur arah motor
void setMotorDirection(bool clockwise) {
    if (clockwise) {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, LOW);
    } else {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
    }
}

// Fungsi untuk menghentikan motor
void stopMotor() {
    analogWrite(ENA, 0);  
    digitalWrite(IN1, LOW);  
    digitalWrite(IN2, LOW);  
}