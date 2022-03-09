#!/bin/bash
#SBATCH --job-name=nerd_co3d
#SBATCH -p gpu
#SBATCH --gres=gpu:1
#SBATCH --qos=normal
#SBATCH -c 8
#SBATCH --output="./co3d_logs/co3d-%a-%j.log"
#SBATCH --open-mode=append
#SBATCH --array="0-10"

scenes=(
backpack_373_41833_83497
handbag_396_49743_97969
handbag_399_51220_100573
hydrant_106_12677_24990
hydrant_268_28513_58093
motorcycle_362_38283_75358
plant_253_27235_55344
plant_372_40884_81286
toytruck_353_37431_70460
toytruck_379_44672_89080
vase_380_44868_89574
)

scene="${scenes[$SLURM_ARRAY_TASK_ID]}"

rwfactor='2'

echo "====== Scene: $scene : $rwfactor ======"

datadir="/export/share/projects/svbrdf/data/co3d_nerd/$scene"

python train_nerd.py --datadir "$datadir" --basedir /export/share/projects/svbrdf/data/co3d_nerd/nerd --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor"
