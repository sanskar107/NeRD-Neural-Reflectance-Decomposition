#!/bin/bash
#SBATCH --job-name=dtu6_nerd
#SBATCH -p g24
#SBATCH --gres=gpu:1
#SBATCH --qos=low
#SBATCH -c 8
#SBATCH --output="./render_dtu_6_logs/dtu_illum6-%a-%j.log"
#SBATCH --open-mode=append
#SBATCH --array="0-14"

# scenes=(
# split16_dtu_illum6_scan122
# split16_dtu_illum6_scan106
# split16_dtu_illum6_scan24
# split16_dtu_illum6_scan83
# split16_dtu_illum6_scan114
# split16_dtu_illum6_scan40
# split16_dtu_illum6_scan105
# split16_dtu_illum6_scan65
# split16_dtu_illum6_scan69
# split16_dtu_illum6_scan37
# split16_dtu_illum6_scan97
# split16_dtu_illum6_scan55
# split16_dtu_illum6_scan110
# split16_dtu_illum6_scan118
# split16_dtu_illum6_scan63
# )

scenes=(
split16_dtu_scan122
split16_dtu_scan106
split16_dtu_scan24
split16_dtu_scan83
split16_dtu_scan114
split16_dtu_scan40
split16_dtu_scan105
split16_dtu_scan65
split16_dtu_scan69
split16_dtu_scan37
split16_dtu_scan97
split16_dtu_scan55
split16_dtu_scan110
split16_dtu_scan118
split16_dtu_scan63
)


scene="${scenes[$SLURM_ARRAY_TASK_ID]}"

rwfactor='2'

echo "====== Scene: $scene : $rwfactor ======"

datadir="/export/share/projects/svbrdf/data/dtu_bmvs_nerd/$scene"
basedir="/export/share/projects/svbrdf/data/dtu_bmvs_nerd/nerd"
other_basedir="/export/share/projects/svbrdf/data/dtu_6_nerd/nerd"

python train_nerd.py --datadir "$datadir" --basedir "$basedir" --other_basedir "$other_basedir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only
