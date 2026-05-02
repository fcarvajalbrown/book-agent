# Math Conversion Rules

Preserve all math exactly. Do not reformat or escape symbols inside math delimiters.

## Inline Math

Markdown `$...$` becomes LaTeX `$...$`.

- Keep single-dollar delimiters.
- Do not add spaces between `$` and the expression.
- Do not wrap in `\text{}`.

## Display Math

Markdown `$$...$$` becomes LaTeX `$$...$$` or `\[...\]`. Either is acceptable; do not mix them in the same fragment.

- Keep multi-line equations intact.
- Do not indent the contents with extra tabs or spaces.

## Environments

If the markdown contains an `align`, `equation`, `gather`, or similar block inside `$$`, preserve the environment name and structure.

## Forbidden Transforms

- Do not escape backslashes inside math: `\nabla` stays `\nabla`, not `\\nabla`.
- Do not convert `\` to `/`.
- Do not remove subscripts or superscripts.
- Do not replace greek letters with unicode equivalents.

## Citations Inside Math

If a citation marker like `(Author, 2024)` appears inside math, move it outside the delimiters.
