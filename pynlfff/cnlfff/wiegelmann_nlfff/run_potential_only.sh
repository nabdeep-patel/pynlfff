#!/bin/bash
#
# Run potential field calculation only (no NLFFF relaxation)
# This uses the Green function solver to compute B0.bin from Bz
#
# Usage: bash run_potential_only.sh PROJECT_DIR GRID SOLVER_DIR
#   PROJECT_DIR: Directory with allboundariesN.dat, gridN.ini files
#   GRID: Grid level to run (1, 2, or 3)
#   SOLVER_DIR: Path to compiled binaries (e.g., ./compiled.cpu.parallel.amd)

set -e  # Exit on error

if [ $# -lt 2 ]; then
    echo "Usage: $0 PROJECT_DIR GRID [SOLVER_DIR]"
    echo ""
    echo "  PROJECT_DIR: Directory containing input files"
    echo "  GRID: Grid level (1, 2, or 3)"
    echo "  SOLVER_DIR: Optional, path to compiled binaries"
    echo "              (default: ./compiled.cpu.parallel.amd)"
    exit 1
fi

PROJECT=$1
GRID=$2
SOLVER_DIR=${3:-./compiled.cpu.parallel.amd}

# Validate project directory
if [ ! -d "$PROJECT" ]; then
    echo "Error: Project directory not found: $PROJECT"
    exit 1
fi

# Validate grid level
if [[ ! "$GRID" =~ ^[123]$ ]]; then
    echo "Error: GRID must be 1, 2, or 3"
    exit 1
fi

# Check for required input files
GRID_FILE="$PROJECT/grid${GRID}.ini"
BOUNDARY_FILE="$PROJECT/allboundaries${GRID}.dat"

if [ ! -f "$GRID_FILE" ]; then
    echo "Error: Grid file not found: $GRID_FILE"
    exit 1
fi

if [ ! -f "$BOUNDARY_FILE" ]; then
    echo "Error: Boundary file not found: $BOUNDARY_FILE"
    exit 1
fi

# Find the prepro executable
PREPRO="$SOLVER_DIR/prepro"
if [ ! -x "$PREPRO" ]; then
    echo "Error: prepro executable not found or not executable: $PREPRO"
    echo "Have you compiled the solver? Run: bash init_compile_ps_amd.sh"
    exit 1
fi

echo "=========================================="
echo "Potential Field Calculation"
echo "=========================================="
echo "Project:  $PROJECT"
echo "Grid:     Level $GRID"
echo "Solver:   $SOLVER_DIR"
echo ""

# Enter project directory (solver expects to run from there)
cd "$PROJECT"

# Copy the requested grid files to working names
echo "Setting up grid level ${GRID}..."
cp "grid${GRID}.ini" "grid.ini"
cp "allboundaries${GRID}.dat" "allboundaries.dat"

# Run the potential field solver (prepro with mode 0 computes Green function)
echo ""
echo "Computing potential field via Green function..."
echo "This may take several minutes for large grids..."
echo ""

"$PREPRO" 0

# Check output
if [ ! -f "B0.bin" ]; then
    echo ""
    echo "Error: B0.bin was not created!"
    exit 1
fi

SIZE=$(du -h B0.bin | cut -f1)
echo ""
echo "=========================================="
echo "Success! Potential field generated."
echo "=========================================="
echo "Output: $PROJECT/B0.bin ($SIZE)"
echo ""
echo "To read the field:"
echo "  from pynlfff.pyproduct.file import NlfffFile"
echo "  r = NlfffFile()"
echo "  B0 = r.read_bin('$PROJECT/B0.bin', '$PROJECT/grid.ini')"
echo ""
