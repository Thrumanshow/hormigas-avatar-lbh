# hormigas-avatar-lbh

Enjambre de 7 hormigas que se comunican con tramas LBH (HMAC-SHA256) y producen audio, visemas y cuadros SVG de un avatar. Solo biblioteca estándar de Python.

## Uso (Termux)
    cd ~/storage/downloads/hormigas-avatar-lbh
    python scripts/run_cycle.py
    python scripts/run_cycle.py "¿Qué es el nodo?" mi-sesion

## Voz (en orden de prioridad)
1. Piper local, si `piper` está en PATH y `PIPER_MODEL` apunta a un modelo `.onnx` (no instala en Termux/Android).
2. espeak-ng local (`pkg install espeak`). Variante por defecto `es-419`; cambia con `export ESPEAK_VOICE=es`.
3. Tono sinusoidal de respaldo (solo stdlib).

El campo `engine` de cada paquete indica cuál se usó.

## Reproducir
- Audio: `termux-media-player play avatars/output/<sesion>_voice.wav` (Termux:API)
- Cuadros: abre `avatars/output/frames/<sesion>/*.svg` en el navegador

## Límites del contrato (.human)
280 caracteres de entrada, 15 s de audio, 60 cuadros. Si una respuesta supera 15 s, la Vigía retiene el paquete: mantén las reglas de `data/knowledge_base.json` por debajo de ~180 caracteres.

## Seguridad
La clave HMAC vive en `~/.hormigas-avatar/lbh.key`, fuera del repo (cambia la ruta con `LBH_KEY_PATH`). Si falta `.human`, el ciclo no arranca.
