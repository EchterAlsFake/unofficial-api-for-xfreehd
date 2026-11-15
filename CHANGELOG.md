# 2.0.0

Release 2.0.0

Update pagination handling, validation, and documentation.

Changes since 1.7.4:

```text
README.md          | 14 +++++++++++
 pyproject.toml     |  4 +--
 xfreehd_api/api.py | 73 +++++++++++++++++++++++++++++++-----------------------
 3 files changed, 58 insertions(+), 33 deletions(-)
```

# Changelog

## 1.7.4 — 2026-10-27

- Normalize bare IDs, relative paths and embed links for videos and albums.
- Return the available video qualities consistently and accept numeric quality aliases.
- Expose private-video status and tolerate optional ratings and duration metadata.
- Handle empty albums safely and reject invalid image page numbers.
- Encode search terms and support sorting and time-frame options.
- Add async client lifecycle support and improve missing-file handling in the CLI.
- Use the published `eaf-base-api>=4.2.5` dependency.

