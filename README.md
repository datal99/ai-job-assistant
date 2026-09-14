# AI Job Assistant

A local FastAPI application that uses a private LaTeX master resume and a job
posting to generate a tailored resume without inventing experience.

## Run locally

```powershell
.venv\Scripts\uvicorn.exe app.main:app --reload
```

Open <http://127.0.0.1:8000> and upload a compatible `.tex` master resume. The
master resume and every generated resume stay under `resumes/`, which is excluded
from Git.

## PDF support

LaTeX viewing and downloading work without extra software. PDF viewing and
downloading require one supported engine on `PATH`:

- Tectonic (recommended for a lightweight local setup)
- `pdflatex`
- `xelatex`
- `lualatex`

You can also set `LATEX_ENGINE` to the full path of a supported executable. See
the [official Tectonic installation guide](https://tectonic-typesetting.github.io/book/latest/getting-started/install.html)
for Windows setup instructions.

For a project-local Windows setup, place `tectonic.exe` in `tools/tectonic/`.
That directory is excluded from Git and detected automatically by the app.
