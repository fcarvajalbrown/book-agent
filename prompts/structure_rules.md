# Document Structure Rules

The output document uses `\documentclass[11pt]{book}`. Your fragment is the body. Map markdown headings to LaTeX sectioning commands as follows:

## Heading Mapping

- `# Section N: Title` → `\chapter{Title}` — strip the leading "Section N:" prefix; the book class auto-numbers chapters.
- `# Title` (the book's top-level title, only the very first `#`) → omit it. The title page is handled by the template.
- `## N.M Title` → `\section{Title}` — strip the leading numeric prefix; LaTeX auto-numbers.
- `### N.M.K Title` → `\subsection{Title}` — strip the leading numeric prefix.
- `#### Title` → `\subsubsection{Title}`.
- `## References` → `\section*{References}` (unnumbered).

Never put a manual section number ("1.1", "2.3.1", "Section 3") inside the title argument. Never emit a raw `#`, `##`, or `###` in body text — these are LaTeX parameter / comment-adjacent characters and break compilation.

## Character Escaping (outside math)

These characters are LaTeX-active. Escape them anywhere they appear in body text (NOT inside `$...$` or `$$...$$`):

| Char | Escape  |
|------|---------|
| `#`  | `\#`    |
| `$`  | `\$`    |
| `%`  | `\%`    |
| `&`  | `\&`    |
| `_`  | `\_`    |
| `{`  | `\{`    |
| `}`  | `\}`    |
| `~`  | `\textasciitilde{}` |
| `^`  | `\textasciicircum{}` |

Backslashes outside math become `\textbackslash{}`. Inside math, leave everything verbatim.

## Figures

Markdown `![alt](path/to/image.png)` becomes:

```latex
\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{path/to/image.png}
\caption{alt text}
\end{figure}
```

Always use `[H]` (capital H, requires `float` package which the template loads) so figures appear inline at the point of reference, not floated to chapter end. Always include `\centering`. Use `width=\textwidth` for full-width figures, `width=0.6\textwidth` for half-width.

## Lists, Emphasis, Code

- `**bold**` → `\textbf{...}`
- `*italic*` or `_italic_` → `\textit{...}`
- Bullet list → `\begin{itemize} \item ... \end{itemize}`
- Numbered list → `\begin{enumerate} \item ... \end{enumerate}`
- Inline `` `code` `` → `\texttt{...}` (escape `_`, `#`, `$`, `&`, `%` inside)
- Fenced code block → `\begin{verbatim} ... \end{verbatim}`

## What Not to Output

- No raw markdown markers (`#`, `**`, `_`, `[`, `]`, `` ` ``) outside their LaTeX equivalents.
- No `\maketitle`, `\tableofcontents`, `\begin{document}`, preamble — the template provides these.
- No invented `\includegraphics{...}` entries — only convert image references that exist in the markdown source.
