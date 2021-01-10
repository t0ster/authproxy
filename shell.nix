{ pkgs ? import <nixpkgs> { } }:

with pkgs;

mkShell { buildInputs = [ poetry python3Packages.brotlipy ]; }
