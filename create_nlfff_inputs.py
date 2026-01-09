#!/usr/bin/env python3
"""
Create NLFFF input files from SHARP CEA Br/Bt/Bp FITS files.

Usage:
    python create_nlfff_inputs.py --bp Bp.fits --bt Bt.fits --br Br.fits --output ./project_dir
"""

import argparse
import sys
import os

# Add pynlfff to path if running from repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pynlfff.pyprepare.prepare_base import PrepareWorker


def main():
    parser = argparse.ArgumentParser(
        description="Create NLFFF solver inputs from SHARP CEA vector magnetogram FITS files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage:
  python create_nlfff_inputs.py --bp Bp.fits --bt Bt.fits --br Br.fits --output ./my_run
  
  # With custom parameters:
  python create_nlfff_inputs.py --bp Bp.fits --bt Bt.fits --br Br.fits \\
                                --output ./my_run --mu 0.05 --nue 0.001

Input FITS files:
  Bp.fits - Phi component (eastward) in Gauss
  Bt.fits - Theta component (southward) in Gauss  
  Br.fits - Radial component (outward) in Gauss

Output files (written to --output directory):
  allboundaries1.dat, allboundaries2.dat, allboundaries3.dat
  grid1.ini, grid2.ini, grid3.ini
  mask1.dat, mask2.dat, mask3.dat
  boundary.ini
"""
    )
    
    parser.add_argument("--bp", required=True, 
                       help="Path to Bp (phi component) FITS file")
    parser.add_argument("--bt", required=True,
                       help="Path to Bt (theta component) FITS file")
    parser.add_argument("--br", required=True,
                       help="Path to Br (radial component) FITS file")
    parser.add_argument("--output", "-o", required=True,
                       help="Output directory for NLFFF input files")
    
    parser.add_argument("--mu", type=float, default=0.1,
                       help="Smoothing parameter (default: 0.1)")
    parser.add_argument("--nd", type=int, default=0,
                       help="Nd parameter (default: 0)")
    parser.add_argument("--nue", type=float, default=0.001,
                       help="Nu parameter (default: 0.001)")
    parser.add_argument("--boundary", type=int, default=0,
                       help="Boundary parameter (default: 0)")
    
    args = parser.parse_args()
    
    # Validate input files exist
    for path, name in [(args.bp, "Bp"), (args.bt, "Bt"), (args.br, "Br")]:
        if not os.path.exists(path):
            print(f"Error: {name} file not found: {path}", file=sys.stderr)
            sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    print(f"Creating NLFFF input files from SHARP cutout...")
    print(f"  Bp: {args.bp}")
    print(f"  Bt: {args.bt}")
    print(f"  Br: {args.br}")
    print(f"  Output: {args.output}/")
    print(f"  Parameters: mu={args.mu}, nd={args.nd}, nue={args.nue}, boundary={args.boundary}")
    print()
    
    # Create worker with specified parameters
    worker = PrepareWorker(mu=args.mu, nd=args.nd, nue=args.nue, boundary=args.boundary)
    
    # Process FITS files
    print("Reading FITS files and generating multi-grid inputs...")
    try:
        worker.prepare_from_fits_Bprt(args.bp, args.bt, args.br, args.output)
    except Exception as e:
        print(f"Error processing FITS files: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print("✓ Successfully created NLFFF input files:")
    
    # List output files
    expected_files = [
        "allboundaries1.dat", "allboundaries2.dat", "allboundaries3.dat",
        "grid1.ini", "grid2.ini", "grid3.ini",
        "mask1.dat", "mask2.dat", "mask3.dat",
        "boundary.ini"
    ]
    
    for fname in expected_files:
        fpath = os.path.join(args.output, fname)
        if os.path.exists(fpath):
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  ✓ {fname:25s} ({size_kb:8.1f} KB)")
        else:
            print(f"  ✗ {fname:25s} (missing!)")
    
    # Read grid sizes
    grid_info = []
    for level in [1, 2, 3]:
        grid_file = os.path.join(args.output, f"grid{level}.ini")
        if os.path.exists(grid_file):
            with open(grid_file, 'r') as f:
                lines = f.read().strip().split('\n')
                # Format: nx\n\t###\nny\n\t###\nnz\n\t###
                try:
                    nx = int(lines[1].strip())
                    ny = int(lines[3].strip())
                    nz = int(lines[5].strip())
                    grid_info.append((level, nx, ny, nz))
                except:
                    pass
    
    if grid_info:
        print()
        print("Grid hierarchy:")
        for level, nx, ny, nz in grid_info:
            npix = nx * ny * nz
            print(f"  Level {level}: {nx:3d} × {ny:3d} × {nz:3d} = {npix:,} voxels")
    
    print()
    print("Next steps:")
    print(f"  1. Compile solver: cd pynlfff/cnlfff/wiegelmann_nlfff && bash init_compile_ps_amd.sh")
    print(f"  2. Run NLFFF:     bash compiled.cpu.parallel.amd/multigrid.sh {os.path.abspath(args.output)} 123")
    print(f"  3. Read results:  from pynlfff.pyproduct.file import NlfffFile; ...")
    print()


if __name__ == "__main__":
    main()
