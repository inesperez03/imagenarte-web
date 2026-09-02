# Imagenarte Web

Primera versión local de una web para tienda de arte y enmarcaciones.

La web está dividida en tres pestañas:

- `Inicio`: presentación de la tienda y servicios.
- `Escaparate`: catálogo filtrable y paginado.
- `Contacto`: vías de contacto y consultas.

## Ejecutar en localhost

```powershell
python server.py
```

Después abre:

```text
http://localhost:5173
```

## Gestión de productos

Pulsa `Gestión` en la cabecera.

Contraseña de demo:

```text
imagenarte
```

Los productos se guardan en `imagenarte.db` y las fotos subidas se guardan como archivos dentro de `uploads/`.

La contraseña local por defecto es `imagenarte`.

## Etiquetas

El panel usa etiquetas fijas para evitar errores al introducir productos:

- `Tipo`: se selecciona una sola opción.
- `Colores`: se pueden seleccionar varios.
- `Grupos`: se pueden seleccionar varios.

Desde el bloque `Etiquetas fijas` del panel de gestión se pueden añadir nuevos tipos, colores o grupos. Las nuevas etiquetas aparecen automáticamente en el formulario y en los filtros del escaparate.

## Backend local

Endpoints principales:

- `GET /api/products`: productos publicados.
- `GET /api/products?all=1`: todos los productos usando la contraseña de gestión.
- `POST /api/products`: crear producto con foto opcional.
- `PUT /api/products/:id`: editar producto.
- `DELETE /api/products/:id`: eliminar producto y su foto subida.
- `GET /api/tags`: listas de tipos, colores y grupos.
- `POST /api/tags`: crear una nueva etiqueta usando la contraseña de gestión.

## Subir a GitHub

GitHub se usa para guardar el código, no para ejecutar este backend Python.

Pasos:

```powershell
git init
git add .
git commit -m "Primera version Imagenarte"
```

Después crea un repositorio vacío en GitHub y conecta el remoto:

```powershell
git remote add origin https://github.com/TU_USUARIO/imagenarte_web.git
git branch -M main
git push -u origin main
```

No se suben `imagenarte.db` ni `uploads/`, porque están en `.gitignore`.

## Desplegar la web

Esta app tiene frontend y backend juntos. No conviene separarla todavía.

Recomendación: desplegarla como servicio Python en Render usando `render.yaml`.

Configuración:

- Build command: vacío.
- Start command: `python server.py`.
- Variable `HOST`: `0.0.0.0`.
- Variable `IMAGENARTE_ADMIN_PASSWORD`: la contraseña real de gestión.
- Disco persistente montado en `/var/data`.
- Variable `IMAGENARTE_DATA_DIR`: `/var/data`.

El disco persistente es importante: sin él, las fotos subidas y la base de datos podrían perderse al reiniciar el servidor.
