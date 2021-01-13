{ pkgs ? import <nixpkgs> { } }:

with pkgs;

mkShell { buildInputs = [ python39Packages.poetry python39Packages.brotlipy ]; }
