from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, ColorSensor
from pybricks.parameters import Port, Color, Direction, Stop
from pybricks.tools import wait

# Inicializar Hub
hub = PrimeHub()

# Sensores y motores
sensor = ColorSensor(Port.B)
motorE = Motor(Port.E)
motorF = Motor(Port.F)
motorA = Motor(Port.A) # principal

# Velocidades
VELOCITY = 720
VELOCITY_SLOW = 720

# Asignación de colores a motor y posición
COLOR_ASSIGNMENTS = {
    Color.RED: (motorE, 0),
    Color.BLUE: (motorE, 180),
    Color.GREEN: (motorF, 0),
    Color.YELLOW: (motorF, 180),
}   
# Estado inicial de motores
motor_positions = {
    motorE: 0,
    motorF: 0,
}

last_color = None
bloques = 0
while bloques<10:
    detected_color = sensor.color()
    if detected_color in COLOR_ASSIGNMENTS:
        bloques+=1
    if detected_color in COLOR_ASSIGNMENTS and detected_color != last_color:
        motor_target, target_pos = COLOR_ASSIGNMENTS[detected_color]
        # Girar motor E o F a posición absoluta
        motor_target.run_target(VELOCITY, target_pos, Stop.HOLD, Direction.CLOCKWISE)

        # Motor A (alimentación)
        if detected_color in (Color.MAGENTA, Color.BLUE):
            motorA.run_angle(VELOCITY_SLOW, 180)
        else:
            motorA.run_angle(VELOCITY_SLOW, -180)

        motor_positions[motor_target] = target_pos
        last_color = detected_color

        wait(150)
    elif detected_color in COLOR_ASSIGNMENTS and detected_color == last_color:

        # Solo motor A porque el color es igual al anterior
        if detected_color in (Color.MAGENTA, Color.BLUE):
            motorA.run_angle(VELOCITY_SLOW, 180)
        else:
            motorA.run_angle(VELOCITY_SLOW, -180)

        last_color = detected_color
        wait(50)

    # Si detecta color no válido → resetear last_color
    elif detected_color not in COLOR_ASSIGNMENTS and detected_color != Color.NONE:
        bloques+=1
        motorA.run_angle(100, 180)
    print(bloques)
    wait(50)