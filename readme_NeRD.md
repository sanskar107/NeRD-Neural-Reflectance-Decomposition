# NeRD Experiments for "ERROR: Evaluation of Reconstruction and Rendering for Object Relighting"

Please, find the modified code base at: https://anonymous.4open.science/r/tensoir-3D3C/README.md

## Dataset

Download and extract the dataset as follows:

```bash
# Folder structure
# data/dataset_raw
# ├── bmvs
# │   ├── bear
# │   ├── clock
# │   ├── dog
# │   ├── durian
# │   ├── jade
# │   ├── man
# │   ├── sculpture
# │   └── stone
# ├── dtu
# │   ├── scan37
# │   ├── scan40
# │   ├── scan55
# │   ├── scan63
# │   ├── scan65
# │   ├── scan69
# │   ├── scan83
# │   └── scan97
# ├── objrel
# │   ├── antman
# │   ├── apple
# │   ├── chest
# │   ├── gamepad
# │   ├── ping_pong_racket
# │   ├── porcelain_mug
# │   ├── tpiece
# │   └── wood_bowl
# └── synth4relight_subsampled
#     ├── air_baloons
#     ├── chair
#     ├── hotdog
#     └── jugs
```

## Data Conversion

Convert the raw data to LLFF format using `scripts/create_nerf_data.py` from `object-relighting-dataset` repository.

```bash
python scripts/create_nerf_data.py data/dataset_raw/$scene/test data/llff_data/$scene --overwrite
```


## Dependencies

Install the author's original dependencies.

```bash
conda env create -f environment.yml
conda activate nerd
```

## Prepare environment maps into spherical gaussians
```bash
scene="antman"
python scripts/fit_sgs.py data/llff_data/$scene/val_envmaps.npy  --gpu 0 --steps 4000
```


## Train, NVS, and Relighting

We provide example commands for running training, novel view synthesis (NVS)
and relighting.

```bash
scene="antman"
rwfactor='2'

datadir="data/llff_data/$scene"
envdir="data/llff_data/$scene/val_envmaps_sgs.npy"
expname=$scene

# train
python train_nerd.py --datadir "$datadir" --basedir "out" --expname "$expname" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --single_env --envmap_path "$envdir"

# relighting
python train_nerd.py --datadir "$datadir" --basedir "out" --expname "$expname" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --single_env --envmap_path "$envdir" --render_only

# novel views
python train_nerd.py --datadir "$datadir" --basedir "out" --expname "$expname" --config configs/nerd/real_world.txt --rwfactor "$rwfactor" --single_env --render_only
```


## Evaluation

We provide lists of files for preparing evaluation.

```bash                  
eval
├── bmvs_nvs.json              # List of files for NVS on BMVS
├── dtu_nvs.json               # List of files for NVS on DTU
├── ord_nvs.json               # List of files for NVS on object-relighting-dataset
├── ord_relight.json           # List of files for relighting on object-relighting-dataset
├── prepare_eval.py            # Copy the files to the evaluation folder
├── synth4relight_nvs.json     # List of files for NVS on synth4relight
└── synth4relight_relight.json # List of files for relighting on synth4relight
``` 

In the file list json files:

- `gt_path`: Path to the ground-truth file
- `pd_dst_path`: Path to the location where the prediction file will be copied
- `pd_src_path`: Path to the prediction file

Run `prepare_eval.py` to copy all `pd_src_path` to `pd_dst_path`.