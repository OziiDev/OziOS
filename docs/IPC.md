# oziwm IPC

`oziwm` ile kabuk (`ozi-shell`), `ozi` komutu ve testler arasındaki sözleşme.

## Bağlantı

- Unix soketi: `$XDG_RUNTIME_DIR/oziwm-<WAYLAND_DISPLAY>.sock`. `oziwm` başlarken yolu
  `OZIWM_SOCKET` ortam değişkeniyle çocuk süreçlere verir.
- Her mesaj tek satır JSON, `\n` ile biter. UTF-8.
- İstemci bir istek yazar, `oziwm` tek satır cevap yazar. `{"subscribe": [...]}` isteğinden
  sonra bağlantı olay akışına döner: bir daha istek okunmaz, yalnız olaylar gelir.

## İstekler

| İstek | Cevap |
|---|---|
| `{"get": "version"}` | `{"ok": {"version": "0.4.0-dev"}}` |
| `{"get": "outputs"}` | `{"ok": [{"name": "eDP-1", "x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 1.0}]}` |
| `{"get": "windows"}` | `{"ok": [Window, ...]}` (en üstteki sonda) |
| `{"get": "workspaces"}` | `{"ok": [{"index": 1, "active": true, "windows": 2}, ...]}` |
| `{"do": "focus", "id": 7}` | `{"ok": null}` |
| `{"do": "close", "id": 7}` | `{"ok": null}` |
| `{"do": "spawn", "command": ["konsole"]}` | `{"ok": null}` |
| `{"do": "workspace", "index": 2}` | `{"ok": null}` |
| `{"do": "quit"}` | `{"ok": null}`, sonra oziwm kapanır |
| `{"subscribe": ["windows", "workspaces"]}` | `{"ok": null}`, sonra olaylar |

Hata: `{"error": "insan okuyabilir açıklama"}`. Bilinmeyen alanlar yok sayılır, bilinmeyen
istek hata döner; böylece eski kabuk yeni oziwm ile çalışır.

`Window`:

```json
{"id": 7, "app_id": "org.kde.konsole", "title": "~ : fish", "workspace": 1,
 "focused": true, "x": 100, "y": 80, "width": 800, "height": 500}
```

`id` oziwm'in verdiği, oturum boyunca tekrar kullanılmayan bir sayıdır.

## Olaylar

```json
{"event": "window-opened", "window": Window}
{"event": "window-changed", "window": Window}
{"event": "window-closed", "id": 7}
{"event": "focus", "id": 7}
{"event": "workspace", "index": 2}
```
