# Quick Start: SHARP Cutout to 3D Coronal Field

## Overview
This guide shows how to extrapolate 3D coronal magnetic fields from SHARP cutout Br/Bt/Bp FITS files.

## Prerequisites
- SHARP CEA cutout FITS files: `Br.fits`, `Bt.fits`, `Bp.fits` (radial, theta, phi components)
- Python 3.7+ with numpy, astropy
- C compiler (gcc) for CPU or nvcc for GPU

---

## Step 1: Prepare Input Files

Your SHARP cutout provides the vector magnetogram at the photosphere. Convert these to the solver's input format:

```bash
python create_nlfff_inputs.py \
  --bp /path/to/your/Bp.fits \
  --bt /path/to/your/Bt.fits \
  --br /path/to/your/Br.fits \
  --output ./my_project
```

This creates:
```
my_project/
├── allboundaries1.dat  # Coarse grid boundary data
├── allboundaries2.dat  # Medium grid boundary data
├── allboundaries3.dat  # Fine grid boundary data
├── grid1.ini          # Coarse grid size (nx, ny, nz)
├── grid2.ini          # Medium grid size
├── grid3.ini          # Fine grid size
├── mask1.dat          # Error mask for coarse grid
├── mask2.dat          # Error mask for medium grid
├── mask3.dat          # Error mask for fine grid
└── boundary.ini       # Preprocessing parameters
```

**Format Details:**
- `allboundariesN.dat`: ASCII file with Bx, By, Bz values (one per line, y-varies-first order)
- `gridN.ini`: Contains nx, ny, nz, mu, nd parameters
- `maskN.dat`: Weight mask (one value per pixel, usually B_transverse/max(B_transverse))

---

## Step 2: Compile the Solver

```bash
cd pynlfff/cnlfff/wiegelmann_nlfff

# For x86_64 Linux (AMD/Intel):
bash ./init_compile_ps_amd.sh

# For ARM Linux:
# bash ./init_compile_ps_arm.sh
```

This compiles three variants:
- `compiled.cpu.nonparallel.{amd|arm}/` - Single-threaded CPU
- `compiled.cpu.parallel.{amd|arm}/` - Multi-threaded CPU (OpenMP)
- `compiled.gpu.nvcc.{amd|arm}/` - GPU accelerated (CUDA)

---

## Step 3: Run Potential Field Extrapolation

Generate the potential field (force-free baseline, uses only Bz/Br):

```bash
cd pynlfff/cnlfff/wiegelmann_nlfff

# Set paths
PROJECT=/absolute/path/to/my_project
GRID=1  # Start with coarse grid

# Choose solver (pick fastest available):
SOLVER=./compiled.cpu.parallel.amd/multigrid.sh

# Run potential field only
bash run_potential_only.sh $PROJECT $GRID $SOLVER
```

**Output:**
- `my_project/B0.bin` - 3D potential field (3×nx×ny×nz doubles)

---

## Step 4: Run NLFFF Extrapolation

Generate the nonlinear force-free field (full 3D coronal solution):

```bash
cd pynlfff/cnlfff/wiegelmann_nlfff

PROJECT=/absolute/path/to/my_project
GRID=123  # Run all three multigrid levels

# Choose solver:
SOLVER=./compiled.cpu.parallel.amd/multigrid.sh
# or for GPU: ./compiled.gpu.nvcc.amd/multigrid.sh

# Run full NLFFF
bash $SOLVER $PROJECT $GRID
```

**What happens:**
1. **Grid 1 (coarse):** Computes potential field → relaxes to NLFFF → outputs Bout1.bin
2. **Grid 2 (medium):** Interpolates Bout1 → relaxes → outputs Bout2.bin
3. **Grid 3 (fine):** Interpolates Bout2 → relaxes → outputs **Bout.bin** (final)

**Outputs:**
- `my_project/Bout.bin` - Final 3D NLFFF field
- `my_project/NLFFFquality1.log` - Quality metrics for grid 1
- `my_project/NLFFFquality2.log` - Quality metrics for grid 2
- `my_project/NLFFFquality3.log` - Quality metrics for grid 3

---

## Step 5: Read and Analyze Results

```python
from pynlfff.pyproduct.file import NlfffFile
import numpy as np

# Read the final NLFFF field
reader = NlfffFile()
B = reader.read_bin(
    bin_path="my_project/Bout.bin",
    grid_path="my_project/grid3.ini",
    memmap=True  # Memory-efficient for large grids
)

# B shape: (3, nx, ny, nz)
# B[0,:,:,:] = Bx
# B[1,:,:,:] = By  
# B[2,:,:,:] = Bz

print(f"Field shape: {B.shape}")
print(f"Field range: {B.min():.2f} to {B.max():.2f} Gauss")

# Optional: Convert to HDF5 for easier analysis
reader.tran_bin2hdf5(
    bin_path="my_project/Bout.bin",
    hdf5_path="my_project/Bout.h5",
    grid_path="my_project/grid3.ini"
)

# Calculate field strength
B_magnitude = np.sqrt(B[0]**2 + B[1]**2 + B[2]**2)
print(f"Max field strength: {B_magnitude.max():.2f} Gauss")

# Energy in the volume (assuming unit spacing in Mm):
dx = dy = dz = 1.0  # Adjust based on your SHARP pixel size
energy = np.sum(B_magnitude**2) * dx * dy * dz / (8 * np.pi)
print(f"Magnetic energy: {energy:.2e} erg")
```

---

## Step 6: Quality Assessment

Check the force-free quality metrics:

```bash
cat my_project/NLFFFquality3.log
```

**Key metrics to check:**
- **CWsin** (current-weighted angle): Should be < 10° for good solutions
- **Divergence** (∇·B): Should approach machine precision
- **Force-free residual** (L): Lower is better
- **Energy**: Compare with potential field energy

---

## Coordinate System Notes

### SHARP CEA Grid
- **Bp** (phi component): Eastward on solar disk
- **Bt** (theta component): Southward on solar disk  
- **Br** (radial component): Outward from solar surface

### Solver Cartesian Grid
The prepare script converts to:
- **Bx** ≈ Bp (eastward, along columns)
- **By** ≈ -Bt (northward, along rows, note sign!)
- **Bz** ≈ Br (upward from photosphere)

Near disk center this mapping is excellent; for limb regions, use the full spherical→Cartesian transform (which `prepare_base.py` handles via the AFI path).

---

## Tips for Best Results

### Grid Sizing
- Start small for testing: ~100×100×100 pixels
- Production runs: Use full SHARP resolution (often 300-800 pixels)
- Ensure nx, ny divisible by 4 (the prepare script enforces this)

### Convergence
- Monitor `NLFFFquality*.log` files during run
- If CWsin remains > 15°, try:
  - Longer relaxation (edit iteration count in multigrid.sh)
  - Preprocessing with `multiprepro` script to reduce net force
  - Adjusting nu, mu parameters in boundary.ini

### Performance
- **Small regions (< 200² pixels):** GPU is fastest
- **Large regions (> 400² pixels):** CPU parallel may be faster due to I/O
- Enable OpenMP: `export OMP_NUM_THREADS=16` before running

### Units
- Keep FITS in Gauss (HMI standard)
- Spatial grid assumed uniform; adjust energy calculations for actual pixel size

---

## Troubleshooting

### "Error grid.ini" or "Error allboundaries.dat"
→ Check that Step 1 completed and created all required files

### Compilation fails
→ Install: `gcc`, `make`, OpenMP (`libomp-dev` on Ubuntu)
→ For GPU: Install CUDA toolkit

### Out of memory
→ Use `memmap=True` when reading bins
→ Or downsample: start with GRID=1 only

### Poor quality (high CWsin)
→ Try preprocessing: `bash multiprepro.cpu.p.amd.sh $PROJECT`
→ Increase iterations in the multigrid script
→ Check for NaN/invalid values in input FITS

---

## Example: Complete Workflow

```bash
# 1. Prepare inputs
python create_nlfff_inputs.py \
  --bp ~/data/SHARP_377/Bp.fits \
  --bt ~/data/SHARP_377/Bt.fits \
  --br ~/data/SHARP_377/Br.fits \
  --output ~/nlfff_run/AR377

# 2. Compile (once)
cd pynlfff/cnlfff/wiegelmann_nlfff
bash ./init_compile_ps_amd.sh

# 3. Run NLFFF
export OMP_NUM_THREADS=16
bash ./compiled.cpu.parallel.amd/multigrid.sh ~/nlfff_run/AR377 123

# 4. Analyze
python -c "
from pynlfff.pyproduct.file import NlfffFile
r = NlfffFile()
B = r.read_bin('~/nlfff_run/AR377/Bout.bin', '~/nlfff_run/AR377/grid3.ini')
print(f'Shape: {B.shape}, Range: [{B.min():.1f}, {B.max():.1f}] G')
"

# 5. Check quality
grep CWsin ~/nlfff_run/AR377/NLFFFquality3.log
```

---

## References

**Method:**
Wiegelmann et al. (2012), Sol. Phys. 281, 37  
DOI: https://doi.org/10.1007/s11207-012-9966-z

**GPU Implementation:**
This repository (deepsolar/pynlfff)  
https://github.com/deepsolar/pynlfff
