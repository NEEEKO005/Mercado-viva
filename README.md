
# Mercado VIVA

## Descripción

Mercado VIVA es un MVP desarrollado para mejorar y agilizar el proceso de devolución de productos.

El sistema permite que un cliente registre una solicitud de devolución y que un empleado pueda consultar, verificar y procesar dicha solicitud.

## Problema

Mercado VIVA presenta un proceso lento para gestionar las devoluciones de productos. El proyecto busca organizar y agilizar este proceso mediante una solución digital.

## Usuarios involucrados

- Cliente
- Empleado de Mercado VIVA

## Objetivo

Agilizar y organizar el proceso de devoluciones de productos, facilitando la solicitud por parte del cliente y la gestión por parte del empleado.

## Alcance del MVP

El sistema permite:

- Solicitar una devolución.
- Registrar los datos del pedido y del producto.
- Consultar las solicitudes registradas.
- Verificar la información de una orden.
- Procesar una devolución.
- Seleccionar entre devolución en efectivo o cambio por la misma unidad.
- Validar datos obligatorios.
- Mostrar mensajes de error y confirmación.

## Historias de usuario

1. Solicitar devolución.
2. Registrar solicitud.
3. Recibir información de confirmación.
4. Verificar orden.
5. Procesar devolución o cambio.

## Tecnologías utilizadas

- HTML
- CSS
- JavaScript
- Python
- Base de datos SQLite
- API para la comunicación entre Front-end y Back-end

## Flujo del sistema

Cliente  
↓  
Front-end  
↓  
API / Back-end  
↓  
Base de datos  
↓  
Back-end  
↓  
Front-end  
↓  
Usuario

## Validaciones

El sistema valida, entre otros aspectos:

- Campos obligatorios.
- Información necesaria para registrar una devolución.
- Cantidad máxima de fotografías permitidas.
- Opciones válidas para procesar la devolución o cambio.

## Pruebas realizadas

### Prueba exitosa

Se registra una solicitud de devolución con la información requerida y el sistema confirma que la solicitud fue registrada correctamente.

### Prueba excepcional

Se intenta enviar el formulario sin ingresar el número de orden. El sistema impide continuar y muestra la validación de campo obligatorio.

## Estructura principal

- `index.html` — Interfaz principal.
- `styles.css` — Estilos de la aplicación.
- `app.js` — Funcionalidad del Front-end.
- `app.py` — Back-end y API.
- `mercado_viva.db` — Base de datos.

## Ejecución

Para ejecutar el proyecto se debe iniciar el servidor mediante `app.py` y acceder desde el navegador a:

`http://localhost:8000`

## Proyecto académico

Proyecto desarrollado como MVP para el proceso de devolución de una compra digital de Mercado VIVA.
