#!/bin/bash -l
## Nazwa zlecenia
#SBATCH -J MPIEratostenes
## Liczba alokowanych węzłów
#SBATCH -N 1
## Liczba zadań per węzeł (domyślnie jest to liczba alokowanych rdzeni na węźle)
#SBATCH --ntasks-per-node=12
## Ilość pamięci przypadającej na jeden rdzeń obliczeniowy (domyślnie 4GB na rdzeń)
#SBATCH --mem-per-cpu=1GB
## Maksymalny czas trwania zlecenia (format HH:MM:SS)
#SBATCH --time=00:05:00 
## Nazwa grantu do rozliczenia zużycia zasobów
#SBATCH -A plgar2022
## Specyfikacja partycji
#SBATCH -p plgrid
## Plik ze standardowym wyjściem
#SBATCH --output="output.out"
## Plik ze standardowym wyjściem błędów
#SBATCH --error="error.err"

srun /bin/hostname

## Zaladowanie modulu IntelMPI w wersji domyslnej
module load scipy-bundle/2021.10-intel-2021b

## przejscie do katalogu z ktorego wywolany zostal sbatch
cd $SLURM_SUBMIT_DIR

mpiexec ./eratostenes.py 1000000