# Post-Quantum Zcash Book

This is the source for the Post-Quantum Zcash book.

## Development

You can render locally and test using `mdbook serve`. The repository's `flake.nix` provides
the tools at the versions that CI uses; from the repository root:

```sh
nix develop
cd book && mdbook serve
```

Without Nix, install the same versions with cargo; `--force` upgrades an older version that
is already installed. The preprocessors must come from the same mdbook generation as mdbook
itself. A 0.4-era preprocessor cannot parse what mdbook 0.5 sends it.

```sh
cargo install --locked --force \
  mdbook@0.5.4 \
  mdbook-katex@0.10.0 \
  mdbook-mermaid@0.17.1
```

The mdbook-admonish preprocessor is not used, since no release of it supports mdbook 0.5.
Its admonition styles are kept in `custom.css`, so a callout can still be written as
`<div class="admonition admonish-note">` with a `<p class="admonition-title">` inside.

Pages can be marked as in-progress by adding `<!-- todo -->` to their line in
`src/SUMMARY.md`, which renders a badge in the sidebar.

## Publication

The `main` branch of this repository, when modified, triggers a GitHub Actions
workflow that builds the book and deploys it to GitHub Pages. The deployment is
disabled while the repository is private.
