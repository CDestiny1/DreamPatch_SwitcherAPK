# Dream Patch Scoreboard Switcher v2

App Android sencilla para enviar por FTP un `DreamPatch_Scoreboard.cpk` a una PS4 con GoldHEN.

## Ruta PS4 corregida

La app **siempre** instala en esta ruta exacta, respetando mayúsculas/minúsculas:

```text
/data/GoldHEN/AFR/CUSA18740/DreamPatch_Scoreboard.cpk
```

No usa `Data/Goldhen`; la v2 usa `/data/GoldHEN/...`.

## Cómo organiza los marcadores en Android

En el almacenamiento interno crea:

```text
ScoreboardsCein/
├── LaLiga Espanola/
│   └── DreamPatch_Scoreboard.cpk
├── Premier League/
│   └── DreamPatch_Scoreboard.cpk
├── Champions League/
│   └── DreamPatch_Scoreboard.cpk
└── Cualquier otro marcador/
    └── DreamPatch_Scoreboard.cpk
```

La lista es **100 % dinámica**. La app no tiene ligas programadas: si agregas o borras carpetas y tocas `Actualizar`, la lista cambia sola. Solo muestra carpetas que realmente contengan `DreamPatch_Scoreboard.cpk`.

## Uso

1. PS4 y teléfono deben estar en la misma red.
2. Activa el servidor FTP de GoldHEN.
3. Abre la app.
4. Configura la IP de la PS4 y puerto (por defecto `2121`).
5. Usa `Probar conexión` para verificar que la PS4 y la ruta estén disponibles.
6. En la pantalla principal toca `Instalar` en el marcador deseado.
7. Confirma y espera a que la barra llegue al 100 %.

La app muestra progreso de subida y, si el servidor FTP soporta el comando `SIZE`, comprueba que el tamaño remoto coincida con el CPK local.

## Android 11+

Para mantener la experiencia sencilla de `Almacenamiento interno/ScoreboardsCein`, la app solicita **Acceso a todos los archivos** en Android 11 o superior. Es una app pensada para instalación directa/sideload, no para publicación en Google Play.

Si no aparecen tus marcadores:

- abre Ajustes del teléfono;
- busca el permiso `Acceso a todos los archivos` de Dream Patch Scoreboard Switcher;
- actívalo;
- vuelve a la app y toca `Actualizar`.

## Compilar APK con GitHub Actions

El proyecto ya incluye `.github/workflows/build.yml`.

1. Sube el contenido del proyecto a un repositorio de GitHub.
2. Abre `Actions`.
3. Ejecuta `Build APK`.
4. Al finalizar descarga el artefacto `scoreboard-switcher-apk`.

También puedes compilar en Linux con Buildozer:

```bash
pip install buildozer cython
buildozer android debug
```

## Verificación antes de instalar (v2.1)

Ahora la app recuerda si ya probaste la conexión con éxito. Si tocas
"Instalar" sin haber usado antes "Probar conexión" en Ajustes, te avisa
que la ruta podría no existir todavía y te deja elegir: ir a Ajustes a
probar, instalar de todos modos, o cancelar. Si cambias la IP, puerto,
usuario o contraseña, se vuelve a pedir la verificación.

## Cambios v2

- Ruta PS4 corregida a `/data/GoldHEN/AFR/CUSA18740/`.
- Escaneo dinámico de carpetas.
- Acceso compatible con Android 11+ mediante `MANAGE_EXTERNAL_STORAGE`.
- Botón para probar FTP y comprobar la ruta antes de instalar.
- Barra de progreso real durante la subida.
- Tamaño visible de cada CPK.
- Verificación del tamaño remoto cuando FTP `SIZE` está disponible.
- Mensajes de error más claros.
- Impide iniciar dos subidas simultáneas.
