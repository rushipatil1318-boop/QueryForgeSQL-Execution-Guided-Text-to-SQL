# Sources and provenance

Primary sources consulted on 2026-10-30. These document the design; their benchmark numbers are not this project's results.

- BIRD official Mini-Dev repository: https://github.com/bird-bench/mini_dev
- Canonical dataset/card: https://huggingface.co/datasets/birdsql/bird_mini_dev
- Pinned annotation revision: `5b256b5a9c17478f06ed6912612e9a14d17065c8`
- Pinned SQLite file: https://huggingface.co/datasets/birdsql/bird_mini_dev/resolve/5b256b5a9c17478f06ed6912612e9a14d17065c8/data/mini_dev_sqlite.jsonl
- Source manifest: https://huggingface.co/datasets/birdsql/bird_mini_dev/blob/5b256b5a9c17478f06ed6912612e9a14d17065c8/data/manifest.json
- Expected annotation SHA-256: `926af2a0d1b47e5d0d15a7aa8a34d4721007f4550a881555b6a89496b54a2606`
- Official set-match evaluator inspected at Git revision `1c49a375e76c471e218564da3f4617513d33e371`: https://github.com/bird-bench/mini_dev/blob/1c49a375e76c471e218564da3f4617513d33e371/evaluation/evaluation_ex.py
- Official-repository-linked database package: https://drive.google.com/file/d/13VLWIwpw5E3d5DUkMvzw7hvHE67a4XkG/view
- SQLite untrusted input guidance: https://www.sqlite.org/security.html
- SQLite PRAGMAs: https://sqlite.org/pragma.html
- Python 3.11 sqlite3 URI, authorizer, limits and progress-handler APIs: https://docs.python.org/3.11/library/sqlite3.html
- SQLGlot documentation: https://sqlglot.com/sqlglot.html
- Ollama Chat API: https://docs.ollama.com/api/chat
- Ollama example model: https://ollama.com/library/qwen2.5-coder:1.5b
- Docker runtime resource controls: https://docs.docker.com/engine/containers/resource_constraints/

The pinned official file contains 500 SQLite instances across 11 database IDs. Its dataset card declares CC-BY-SA-4.0. We do not redistribute those annotations, databases or provider responses in the source archive. Keep attribution and comply with the external data terms when sharing derived material. MIT applies to this repository's code and original teaching fixtures, not to BIRD or model weights.

BIRD citation:

Jinyang Li et al. *Can LLM Already Serve as a Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs*. NeurIPS. Use the official source's BibTeX when preparing a paper.
