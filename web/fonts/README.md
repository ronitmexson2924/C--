# Self-hosted web fonts

Latin-subset variable WOFF2 files, from the [Fontsource](https://fontsource.org) distributions:

| File | Family | License |
|---|---|---|
| `inter-latin-wght-normal.woff2` | [Inter](https://github.com/rsms/inter) | SIL Open Font License 1.1 |
| `jetbrains-mono-latin-wght-normal.woff2` | [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) | SIL Open Font License 1.1 |
| `jetbrains-mono-latin-wght-italic.woff2` | JetBrains Mono Italic | SIL Open Font License 1.1 |

Self-hosting avoids a render-blocking third-party stylesheet and lets the
Content-Security-Policy restrict fonts to `'self'`.
