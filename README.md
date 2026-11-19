# hormigas-avatar-lbh

Enjambre de 7 hormigas que comunican por tramas LBH y producen audio + visemas + cuadros SVG de un avatar. Solo biblioteca estandar de Python.

## Uso (Termux)
    cd ~/storage/downloads/hormigas-avatar-lbh
    python scripts/run_cycle.py
    python scripts/run_cycle.py "Hola, que es LBH?" mi-sesion

## Opcional
- Voz real: `export PIPER_MODEL=/ruta/modelo.onnx` (requiere `piper` en PATH). Sin Piper usa un tono de respaldo.
- Audio: `termux-media-player play avatars/output/<sesion>_voice.wav` (Termux:API).
- Cuadros: abre `avatars/output/frames/<sesion>/*.svg` en el navegador.

## Seguridad
La clave HMAC se guarda en `~/.hormigas-avatar/lbh.key` (fuera del repo). Cambia la ruta con `LBH_KEY_PATH`.
Si falta `.human`, el ciclo no arranca.
