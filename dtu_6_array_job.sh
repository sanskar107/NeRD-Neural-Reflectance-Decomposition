#!/bin/bash
#SBATCH --job-name=dtu6_nerd
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --qos=normal
#SBATCH -c 8
#SBATCH --output="./dtu_6_logs/dtu-%a-%j.log"
#SBATCH --open-mode=append
#SBATCH --array="0-14"

scenes=(
split16_dtu_illum6_scan122
split16_dtu_illum6_scan106
split16_dtu_illum6_scan24
split16_dtu_illum6_scan83
split16_dtu_illum6_scan114
split16_dtu_illum6_scan40
split16_dtu_illum6_scan105
split16_dtu_illum6_scan65
split16_dtu_illum6_scan69
split16_dtu_illum6_scan37
split16_dtu_illum6_scan97
split16_dtu_illum6_scan55
split16_dtu_illum6_scan110
split16_dtu_illum6_scan118
split16_dtu_illum6_scan63
)

scene="${scenes[$SLURM_ARRAY_TASK_ID]}"

rwfactor='2'

echo "====== Scene: $scene : $rwfactor ======"

datadir="/export/share/projects/svbrdf/data/dtu_6_nerd/$scene"

python train_nerd.py --datadir "$datadir" --basedir /export/share/projects/svbrdf/data/dtu_6_nerd/nerd --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor"
