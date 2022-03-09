#!/bin/bash
#SBATCH --job-name=rel-nerd
#SBATCH --qos=high
#SBATCH -p g24
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --output="./relight_logs/hyd-%j.log"
#SBATCH --open-mode=append


# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/handbag_396_49743_97969 --basedir holdout_16 --expname handbag_396_49743_97969 --config configs/nerd/real_world.txt --rwfactor 2 --render_only
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/hydrant_106_12677_24990 --basedir holdout_16 --expname hydrant_106_12677_24990 --config configs/nerd/real_world.txt --rwfactor 2 --render_only --envmap_path /home/sanskara/16_NeRD/sgs/hotel_room_1k_sg.npy
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/hydrant_268_28513_58093 --basedir holdout_16 --expname hydrant_268_28513_58093 --config configs/nerd/real_world.txt --rwfactor 2 --render_only
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/motorcycle_362_38283_75358 --basedir exp_debug_motorcycle_1gpu_allholdout --expname motorcycle_362_38283_75358 --config configs/nerd/real_world.txt --rwfactor 2 --render_only
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/plant_253_27235_55344 --basedir holdout_16 --expname plant_253_27235_55344 --config configs/nerd/real_world.txt --rwfactor 2 --render_only
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/plant_372_40884_81286 --basedir holdout_16 --expname plant_372_40884_81286 --config configs/nerd/real_world.txt --rwfactor 2 --render_only
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/toytruck_353_37431_70460 --basedir holdout_16 --expname toytruck_353_37431_70460 --config configs/nerd/real_world.txt --rwfactor 2 --render_only
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/toytruck_379_44672_89080 --basedir holdout_16 --expname toytruck_379_44672_89080 --config configs/nerd/real_world.txt --rwfactor 2 --render_only --envmap_path /home/sanskara/16_NeRD/sgs/hotel_room_1k_sg.npy

# python train_nerd.py --datadir /export/work/sanskara/svbrdf/antman1/ --basedir antman --expname antman2 --config configs/nerd/real_world.txt --rwfactor 2 --render_only --envmap_path /home/sanskara/16_NeRD/sgs/hotel_room_1k_sg.npy
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/antman1/ --basedir antman --expname antman2 --config configs/nerd/real_world.txt --rwfactor 2 --render_only --envmap_path /home/sanskara/16_NeRD/sgs/shanghai_bund_024_sg.npy

# python train_nerd.py --datadir /export/share/projects/svbrdf/data/dtu_bmvs_nerd/split16_dtu_scan65 --basedir dtu_bmvs --expname split16_dtu_scan65 --config configs/nerd/real_world.txt --rwfactor 2 --render_only  --envmap_path /home/sanskara/16_NeRD/sgs/hotel_room_1k_sg.npy
# python train_nerd.py --datadir /export/share/projects/svbrdf/data/dtu_bmvs_nerd/split16_dtu_scan65 --basedir dtu_bmvs --expname split16_dtu_scan65 --config configs/nerd/real_world.txt --rwfactor 2 --render_only  --envmap_path /home/sanskara/16_NeRD/sgs/shanghai_bund_024_sg.npy

# python train_nerd.py --datadir /export/share/projects/svbrdf/data/dtu_bmvs_nerd/split16_bmvs_clock --basedir dtu_bmvs --expname split16_bmvs_clock --config configs/nerd/real_world.txt --rwfactor 2 --render_only  --envmap_path /home/sanskara/16_NeRD/sgs/hotel_room_1k_sg.npy
# python train_nerd.py --datadir /export/share/projects/svbrdf/data/dtu_bmvs_nerd/split16_bmvs_clock --basedir dtu_bmvs --expname split16_bmvs_clock --config configs/nerd/real_world.txt --rwfactor 2 --render_only  --envmap_path /home/sanskara/16_NeRD/sgs/shanghai_bund_024_sg.npy

python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/hydrant_106_12677_24990 --basedir holdout_16 --expname hydrant_106_12677_24990 --config configs/nerd/real_world.txt --rwfactor 2 --render_only --envmap_path /home/sanskara/16_NeRD/sgs/hotel_room_1k_sg.npy
# python train_nerd.py --datadir /export/work/sanskara/svbrdf/data/NeRD/co3d/NeRD/NeRD/hydrant_106_12677_24990 --basedir holdout_16 --expname hydrant_106_12677_24990 --config configs/nerd/real_world.txt --rwfactor 2 --render_only --envmap_path /home/sanskara/16_NeRD/sgs/shanghai_bund_024_sg.npy
