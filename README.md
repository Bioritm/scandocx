# gost-precheck-pro

High-performance offline precheck for GOST 2.105-2019 / GOST 34 with parallel processing,
configurable rules, fast DOCX parser, and folder watcher.

## Quick start

```bash
python -m pip install .
gost-precheck check /path/to/file.docx
gost-precheck check /path/to/folder --recursive
gost-precheck watch /path/to/incoming
```
