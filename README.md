# Generador de EDT (Estructura de Desglose de Trabajo)

Este es un generador de diagramas EDT hecho en Python. Toma un archivo de texto con una lista jerárquica de tareas y genera un diagrama profesional en formato PNG.

## Características

- Genera diagramas EDT con estética profesional.
- Soporta múltiples niveles de jerarquía (1, 1.1, 1.1.1, etc.).
- Diseño híbrido: primer nivel horizontal y subniveles verticales para mayor claridad.
- Cajas con ID y descripción separada.
- Fondo con rejilla y diseño premium.

## Requisitos

- Python 3.x
- Librería Pillow

Puedes instalar la dependencia necesaria con:
```bash
pip install Pillow
```

## Uso

Para generar un diagrama, ejecuta el script pasando el archivo de texto como argumento:

```bash
python generator_edt.py archivo.txt
```

Esto generará un archivo llamado `archivoEDT.png`.

## Formato del archivo de entrada

El archivo de texto debe tener cada elemento en una línea, comenzando con su número jerárquico:

```text
1. Gestión del Proyecto
1.1. Planificación
1.1.1. Definición del alcance
1.2. Ejecución
2. Desarrollo de Software
...
```