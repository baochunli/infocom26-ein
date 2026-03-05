# INFOCOM 2026 Workshop on Embodied Intelligence Networks

This repository contains the source code for the [INFOCOM 2026 Workshop on Embodied Intelligence Networks](https://infocom26-ein.netlify.app/) website.

## Scripts

The `scripts/` directory contains helper scripts for generating the downloadable workshop program files from the website content.

In this workflow, `program.html` is the canonical source of truth for the workshop program. The Word and PDF files are generated artifacts derived from the HTML content and the Word template.

### `scripts/generate-program.py`

This script rebuilds `ein26-program.docx` from:

- `program.html` for the title, description, room, session times, and paper list
- `committee.html` for the committee and chairs section
- `assets/files/workshop-program-template.docx` for the Word layout, paragraph formatting, and fonts

It writes:

- `assets/files/ein26-program.docx`

### Prerequisites

- `pandoc`
- `xelatex` if you also want to regenerate the PDF

### Generate the program in Microsoft Word format

From the repository root:

```bash
uv run scripts/generate-program.py
```

### Generate the program in PDF format

From the repository root:

```bash
uv run scripts/generate-program.py
pandoc assets/files/ein26-program.docx --pdf-engine=xelatex -V mainfont=Helvetica -o assets/files/ein26-program.pdf
```

### Typical workflow

1. Edit `program.html` if the schedule, room, or description changes.
2. Edit `committee.html` if the committee or chairs change.
3. Run the script to rebuild the `.docx`.
4. Run the `pandoc` command above to refresh the PDF.
5. Commit the updated HTML and generated files together.
