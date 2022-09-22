#!/bin/bash
#SBATCH --job-name=vid-nerd
#SBATCH --qos=low
#SBATCH -p g24
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --output="./video_logs/antman1/render-%a-%j.log"
#SBATCH --open-mode=append
#SBATCH --array="0-359"

# antman1,antman1,0
# bottle_44_2232_6712,bottle44,0
# handbag_396_49743_97969,handbag396,0
# hydrant_106_12677_24990,hydrant106,256
# parkingmeter_425_59343_114810,parkingmeter425,0
# plant_253_27235_55344,plant253,0
# toaster_372_41229_82130,toaster372,0
# toytruck_353_37431_70460,toytruck353,0
# vase_149_16568_31914,vase149,0
# split16_dtu_scan106,dtu_scan106,0
# split16_dtu_scan110,dtu_scan110,0
# split16_dtu_scan118,dtu_scan118,0

idxs=($(seq 0 1 359))

idx="${idxs[$SLURM_ARRAY_TASK_ID]}"
echo "====== Index: $idx ======"
# change rwfactor for bmvs scenes

# scene="hydrant_106_12677_24990"
# fix_pose_idx="256"
# shortname="hydrant106"
# datadir="/export/share/projects/svbrdf/data/co3d_nerd/$scene"
# checkpoint_dir="./video_checkpoints"
# rwfactor="2"

scene="antman1"
fix_pose_idx="0"
shortname="antman1"
datadir="/export/share/projects/svbrdf/data/co3d_nerd/$scene"
checkpoint_dir="/export/share/projects/svbrdf/data/co3d_nerd/nerd"
rwfactor="2"

# scene="plant_253_27235_55344"
# fix_pose_idx="0"
# shortname="plant253"
# datadir="/export/share/projects/svbrdf/data/co3d_nerd/$scene"
# checkpoint_dir="/export/share/projects/svbrdf/data/co3d_nerd/nerd"
# rwfactor="2"


# python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --shortname "$shortname" --pose_idx "$idx"
# python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/00203_OpenfootageNET_mirabell_SMALL.hdr --shortname "$shortname" --pose_idx "$idx"
# python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/bathroom_1k.hdr --shortname "$shortname" --pose_idx "$idx"
# python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/kiara_9_dusk_1k.hdr --shortname "$shortname" --pose_idx "$idx"
# python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/reichstag_1_1k.hdr --shortname "$shortname" --pose_idx "$idx"

python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/00203_OpenfootageNET_mirabell_SMALL.hdr --shortname "$shortname" --pose_idx "$idx" --fix_pose_idx "$fix_pose_idx"
python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/bathroom_1k.hdr --shortname "$shortname" --pose_idx "$idx" --fix_pose_idx "$fix_pose_idx"
python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/kiara_9_dusk_1k.hdr --shortname "$shortname" --pose_idx "$idx" --fix_pose_idx "$fix_pose_idx"
python train_nerd.py --datadir "$datadir" --basedir "$checkpoint_dir" --expname "$scene" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --render_only --envmap_path /home/sanskara/16_NeRD/relighting_envmaps/reichstag_1_1k.hdr --shortname "$shortname" --pose_idx "$idx" --fix_pose_idx "$fix_pose_idx"
