# Third-party notices

**Estado:** borrador; la licencia del paquete Termux debe aclararse antes de afirmar un identificador definitivo o redistribuir el motor.

## eSpeak NG — síntesis de voz

El avatar puede invocar `espeak-ng` o `espeak` instalado externamente en el entorno del usuario. La instalación de Termux revisada reportó el paquete `espeak` 1.52.0-1 para `aarch64`; el ejecutable reportó eSpeak NG 1.52.0. El motor y sus datos de voz no se deben considerar incluidos en este repositorio salvo que se añadan expresamente.

Hay una discrepancia pendiente entre las fuentes de licencia consultadas:

- El README y el archivo COPYING de eSpeak NG en la etiqueta 1.52.0 indican GPL-3.0-or-later: https://github.com/espeak-ng/espeak-ng/blob/1.52.0/README.md
- La receta de empaquetado de Termux consultada indica `GPL-2.0` para `espeak` 1.52.0, revisión 1: https://github.com/termux/termux-packages/blob/master/packages/espeak/build.sh
- La ficha local de `dpkg` de la instalación revisada no mostró un campo de licencia ni archivos `copyright`, `COPYING` o `LICENSE`.

Por esta discrepancia, la licencia aplicable al paquete instalado queda **pendiente de confirmación**. Este aviso no selecciona una de las dos declaraciones como definitiva ni concede derechos adicionales. Antes de redistribuir o empaquetar el motor, sus bibliotecas o sus datos, confirmar los términos aplicables con el proyecto y/o el distribuidor del paquete.

## Datos de voz

La instalación revisada contiene el directorio `espeak-ng-data`, y el comando de voces enumeró, entre otras, `es` y `es-419`. No se confirmó qué voz concreta seleccionó el avatar ni se establecieron términos separados para cada archivo de datos. Revisar el paquete y sus avisos aplicables antes de redistribuir esos datos.

## Archivos de audio generados

Los WAV de prueba revisados en `avatars/output/` estaban ignorados por Git y no estaban en el índice en el momento de la comprobación. Son salidas generadas localmente, no el ejecutable ni el modelo del motor. Revisar el estado del repositorio nuevamente antes de cualquier distribución.

## Piper

En la sesión revisada, `PIPER_MODEL` no estaba definido y no se encontró el ejecutable `piper`. No se identifica aquí ningún modelo Piper en uso. Si se configura Piper después, registrar por separado el motor, el modelo y sus datos con sus fuentes y términos exactos.
