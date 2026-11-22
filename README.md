# hormigas-avatar-lbh

Enjambre de 7 hormigas que se comunican con tramas LBH (HMAC-SHA256) y producen audio, visemas y cuadros SVG de un avatar que habla. Corre 100% local en Termux/Android y solo usa la biblioteca estándar de Python.

## Cómo funciona

Cada ciclo pasa una entrada de texto por la cadena de hormigas. Cada una emite una trama LBH firmada que la siguiente verifica antes de actuar:

    Exploradora -> Razonadora -> Voz -> Fonemas -> Render -> Vigía -> Reina

- **Exploradora:** limpia la entrada, valida límites y clasifica el tema.
- **Razonadora:** busca la mejor respuesta en la base de conocimiento (coincidencia puntuada con alias).
- **Voz:** sintetiza el audio `.wav` en local.
- **Fonemas:** convierte el texto en una secuencia de visemas (formas de boca).
- **Render:** dibuja los cuadros SVG del avatar.
- **Vigía:** verifica toda la cadena (firmas, hashes, límites, contrato `.human`) y retiene el paquete si algo falla.
- **Reina:** consolida el paquete final solo si la Vigía lo aprobó.

### Canal de feromonas

La Razonadora comparte su conocimiento con el resto del enjambre emitiendo una trama de tipo `KNOWLEDGE_PHEROMONE` (señal 80, una extensión local de este repo; no forma parte de las tramas base del SDK público). La trama lleva la base de conocimiento y su SHA-256, firmada con HMAC. La Exploradora y la Voz la adoptan solo si la firma, el rol emisor y el hash son válidos. La Vigía comprueba además (`knowledge_in_sync`) que la Exploradora y la Razonadora usaron la misma versión.

## Uso (Termux)

    cd ~/storage/downloads/hormigas-avatar-lbh
    python scripts/run_cycle.py
    python scripts/run_cycle.py "¿Qué es el nodo?" mi-sesion

Chat interactivo, con voz si hay Termux:API:

    python scripts/chat.py

Comandos del chat: `/ayuda`, `/silencio`, `/stats`, `/salir`.

## Base de conocimiento

`data/knowledge_base.json`:

    {
      "default": "Respuesta si ninguna regla coincide",
      "rules":   { "tema": "Respuesta breve" },
      "aliases": { "tema": ["sinónimo", "frase completa"] },
      "pronunciacion": { "SIGLA": "como se lee en voz alta" },
      "velocidad": { "tema": 140 }
    }

- **Puntuación:** frase completa (4), palabra exacta (3), inicio de palabra (2), subcadena (1). En empate gana la primera regla del archivo.
- **`pronunciacion`:** cambia solo el texto que se lee en voz alta; la pantalla conserva el original.
- **`velocidad`:** palabras por minuto de espeak para una regla concreta (100 a 220; por defecto 160).
- **Longitud:** mantén cada respuesta por debajo de ~150 caracteres; con la voz actual, respuestas más largas se acercan al límite de 15 s.

## Voz (en orden de prioridad)

1. Piper local, si `piper` está en PATH y `PIPER_MODEL` apunta a un modelo `.onnx` (no se instala en Termux/Android).
2. espeak-ng local (`pkg install espeak`). Variante por defecto `es-419`; cambia con `export ESPEAK_VOICE=es`.
3. Tono sinusoidal de respaldo (solo stdlib).

El campo `engine` de cada paquete indica cuál se usó.

## Reproducir

- Audio: `termux-media-player play avatars/output/<sesion>_voice.wav` (Termux:API)
- Cuadros: abre `avatars/output/frames/<sesion>/*.svg` en el navegador

## Límites del contrato (.human)

280 caracteres de entrada, 15 s de audio, 60 cuadros. Si algo los supera, o si falta `.human`, el ciclo no entrega el paquete.

## Seguridad

La clave HMAC vive en `~/.hormigas-avatar/lbh.key`, fuera del repo (cambia la ruta con `LBH_KEY_PATH`). Las salidas, los logs y las claves están en `.gitignore`.

## Protocolo LBH

LBH (Lenguaje Binario HormigasAIS) es un protocolo binario abierto con especificación pública y SDKs oficiales. SDK de Python: https://pypi.org/project/lbh-sdk/

## Licencia

Mozilla Public License 2.0 (MPL-2.0). Ver `LICENSE`.

Copyright (c) Cristhiam Leonardo Hernández Quiñonez (CLHQ).
