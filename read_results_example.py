#!/usr/bin/env python3
"""
Example script to read and analyze NLFFF results.

Usage:
    python read_results_example.py /path/to/project_dir
"""

import sys
import os
import numpy as np

# Add pynlfff to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pynlfff.pyproduct.file import NlfffFile


def read_quality_log(logfile):
    """Parse NLFFFquality.log file."""
    if not os.path.exists(logfile):
        return None
    
    metrics = {}
    with open(logfile, 'r') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, val = line.split(':', 1)
                try:
                    metrics[key.strip()] = float(val.strip())
                except:
                    metrics[key.strip()] = val.strip()
    return metrics


def analyze_field(project_dir):
    """Analyze NLFFF results from a project directory."""
    
    print("="*70)
    print("NLFFF Results Analysis")
    print("="*70)
    print(f"Project: {project_dir}\n")
    
    # Check which files exist
    has_b0 = os.path.exists(os.path.join(project_dir, "B0.bin"))
    has_bout = os.path.exists(os.path.join(project_dir, "Bout.bin"))
    has_grid3 = os.path.exists(os.path.join(project_dir, "grid3.ini"))
    
    if not has_grid3:
        print("Error: grid3.ini not found!")
        return
    
    reader = NlfffFile()
    
    # Read grid info
    grid_path = os.path.join(project_dir, "grid3.ini")
    nxyz = reader.get_size_from_grid(grid_path)
    nx, ny, nz = nxyz
    
    print(f"Grid size: {nx} × {ny} × {nz} = {nx*ny*nz:,} voxels")
    print()
    
    # Analyze potential field if exists
    if has_b0:
        print("-" * 70)
        print("Potential Field (B0.bin)")
        print("-" * 70)
        
        B0 = reader.read_bin(
            os.path.join(project_dir, "B0.bin"),
            grid_path,
            memmap=True
        )
        
        Bx0, By0, Bz0 = B0[0], B0[1], B0[2]
        B0_mag = np.sqrt(Bx0**2 + By0**2 + Bz0**2)
        
        print(f"Bx range: [{Bx0.min():8.2f}, {Bx0.max():8.2f}] G")
        print(f"By range: [{By0.min():8.2f}, {By0.max():8.2f}] G")
        print(f"Bz range: [{Bz0.min():8.2f}, {Bz0.max():8.2f}] G")
        print(f"|B| range: [{B0_mag.min():8.2f}, {B0_mag.max():8.2f}] G")
        print(f"|B| mean:  {B0_mag.mean():8.2f} G")
        
        # Energy (assuming unit spacing, result in arbitrary units)
        energy0 = np.sum(B0_mag**2)
        print(f"Energy (integrated |B|²): {energy0:.3e}")
        print()
    
    # Analyze NLFFF field if exists
    if has_bout:
        print("-" * 70)
        print("NLFFF Field (Bout.bin)")
        print("-" * 70)
        
        B = reader.read_bin(
            os.path.join(project_dir, "Bout.bin"),
            grid_path,
            memmap=True
        )
        
        Bx, By, Bz = B[0], B[1], B[2]
        B_mag = np.sqrt(Bx**2 + By**2 + Bz**2)
        
        print(f"Bx range: [{Bx.min():8.2f}, {Bx.max():8.2f}] G")
        print(f"By range: [{By.min():8.2f}, {By.max():8.2f}] G")
        print(f"Bz range: [{Bz.min():8.2f}, {Bz.max():8.2f}] G")
        print(f"|B| range: [{B_mag.min():8.2f}, {B_mag.max():8.2f}] G")
        print(f"|B| mean:  {B_mag.mean():8.2f} G")
        
        # Energy
        energy = np.sum(B_mag**2)
        print(f"Energy (integrated |B|²): {energy:.3e}")
        
        if has_b0:
            ratio = energy / energy0
            print(f"Energy ratio (NLFFF/Potential): {ratio:.4f}")
        print()
        
        # Calculate some force-free diagnostics
        print("-" * 70)
        print("Force-Free Diagnostics")
        print("-" * 70)
        
        # Current-weighted sine (simplified, full calculation needs proper derivatives)
        # This is a very rough estimate
        eps = 1e-10
        jx = (Bz[1:-1, 2:, 1:-1] - Bz[1:-1, :-2, 1:-1]) - (By[1:-1, 1:-1, 2:] - By[1:-1, 1:-1, :-2])
        jy = (Bx[1:-1, 1:-1, 2:] - Bx[1:-1, 1:-1, :-2]) - (Bz[2:, 1:-1, 1:-1] - Bz[:-2, 1:-1, 1:-1])
        jz = (By[2:, 1:-1, 1:-1] - By[:-2, 1:-1, 1:-1]) - (Bx[1:-1, 2:, 1:-1] - Bx[1:-1, :-2, 1:-1])
        
        j_mag = np.sqrt(jx**2 + jy**2 + jz**2) + eps
        bx_c = Bx[1:-1, 1:-1, 1:-1]
        by_c = By[1:-1, 1:-1, 1:-1]
        bz_c = Bz[1:-1, 1:-1, 1:-1]
        b_mag_c = np.sqrt(bx_c**2 + by_c**2 + bz_c**2) + eps
        
        cos_angle = (jx*bx_c + jy*by_c + jz*bz_c) / (j_mag * b_mag_c)
        angle = np.arccos(np.clip(cos_angle, -1, 1)) * 180 / np.pi
        
        # Current-weighted average
        weight = j_mag * b_mag_c
        cwsin = np.sum(np.sin(angle * np.pi/180) * weight) / np.sum(weight)
        cwsin_deg = np.arcsin(cwsin) * 180 / np.pi
        
        print(f"Current-weighted angle (J∥B): {cwsin_deg:.2f}° (estimate)")
        print("  (< 10° is good, < 5° is excellent)")
        print()
    
    # Read quality logs
    print("-" * 70)
    print("Quality Metrics from Logs")
    print("-" * 70)
    
    for level in [1, 2, 3]:
        logfile = os.path.join(project_dir, f"NLFFFquality{level}.log")
        if os.path.exists(logfile):
            print(f"\nGrid Level {level}:")
            metrics = read_quality_log(logfile)
            if metrics:
                for key, val in metrics.items():
                    if isinstance(val, float):
                        print(f"  {key:20s}: {val:.6f}")
                    else:
                        print(f"  {key:20s}: {val}")
    
    print()
    print("="*70)
    print("Analysis complete!")
    print("="*70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python read_results_example.py /path/to/project_dir")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    
    if not os.path.isdir(project_dir):
        print(f"Error: Directory not found: {project_dir}")
        sys.exit(1)
    
    analyze_field(project_dir)


if __name__ == "__main__":
    main()
