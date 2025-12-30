# Manual de Usuario 
## Sporting Mining: Clasificador Remoto de Minerales para la Optimización y Seguridad en Minería

### Descripción 
**Sporting Mining** es un prototipo diseñado para clasificar minerales representados por piezas de colores mediante un sensor de color. El sistema busca optimizar la clasificación, mejorar la precisión y aumentar la seguridad operacional a través del control remoto y la automatización. 

--- 

### Características 
- Detecta piezas por color a través de un **sensor de color**. 
- Clasifica las piezas en **contenedores específicos** según el color detectado. 
- Permite **control remoto** del prototipo vía **Bluetooth**. 
- Dispone de un **modo automático** de clasificación de piezas. 
- Incluye una **interfaz gráfica de usuario (GUI)** para el manejo del prototipo. 
- Soporta **casos particulares de piezas de colores** fuera del rango estándar. 

--- 

### Requerimientos necesarios 
- **Sistema operativo:** Windows 11 
- **Conectividad:** Bluetooth 

--- 

### Pasos de instalación y configuración 
1. **Instalar dependencias** 
    - Descargar e instalar **Python 3.12.4**. 
    - Descargar e instalar la **última versión de Visual Studio Code (VS Code)**. 
    - Descargar e instalar la **última versión de PyBricks** y sus extensiones correspondientes en VS Code. 

2. **Preparar el entorno del dispositivo** 
    - Formatear el **Spike Prime HUB** utilizando PyBricks.

3. **Obtener y abrir el código fuente** 
    - Descargar el **código fuente** desde el repositorio de GitHub. 
    - Guardar el proyecto en una carpeta de fácil acceso. 
    - Abrir esa carpeta dentro de **Visual Studio Code**. 

4. **Establecer conexión Bluetooth** 
    - Activar la **conexión Bluetooth** en el PC. 
    - Encender el **HUB** y verificar que el **botón de Bluetooth** esté **encendido y parpadeando**. 

5. **Ejecutar la interfaz gráfica** 
    - Compilar el archivo correspondiente a la **interfaz gráfica**. 
    - Dentro de la GUI, **conectarse con el HUB** mientras el botón de Bluetooth siga parpadeando. 

6. **Pruebas y ejecución** 
    - Realizar las **pruebas funcionales necesarias**. 
    - Iniciar la **ejecución de las tareas de clasificación automática**. 

--- 

### Recomendaciones 
    - Verificar siempre la conexión Bluetooth antes de ejecutar el programa. 
    - Reiniciar el HUB si se presentan errores de comunicación.
