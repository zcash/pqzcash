{
  description = "Post-Quantum Zcash: book rendering environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            # The book: mdbook and the preprocessors that book/book.toml names. nixpkgs keeps
            # the plugins compatible with its mdbook, which cargo-installed versions need not be.
            pkgs.mdbook
            pkgs.mdbook-katex
            pkgs.mdbook-mermaid

            # The todo preprocessor and the study's scripts.
            pkgs.python3
          ];

          shellHook = ''
            echo "Post-Quantum Zcash rendering environment"
            echo "  (cd book && mdbook serve)   - render the book locally"
            echo "  (cd book && mdbook build)   - build the book into book/book"
          '';
        };
      }
    );
}
