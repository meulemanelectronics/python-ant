with import <nixpkgs> {};
let python = python3.withPackages(ps: with ps;
      [ setuptools pyserial pyusb msgpack six future pygame ]);
in stdenv.mkDerivation {
  name = "biscuit";
  PYTHONPATH = "./src";
  buildInputs = [ python dejavu_fonts ];
  FONT = "${dejavu_fonts}/share/fonts/truetype/DejaVuSansMono-Bold.ttf";
}
