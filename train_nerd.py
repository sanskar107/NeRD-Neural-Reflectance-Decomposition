import os
from typing import Callable, List, Dict

import imageio
import numpy as np
import tensorflow as tf
import cv2
from tqdm import tqdm
from scipy.spatial.transform import Rotation

import dataflow.nerd as data
import nn_utils.math_utils as math_utils
import utils.training_setup_utils as train_utils
from models.nerd_net import NerdModel
from nn_utils.nerf_layers import get_full_image_eval_grid
from nn_utils.tensorboard_visualization import hdr_to_tb, horizontal_image_log, to_8b


def add_args(parser):
    parser.add_argument(
        "--log_step",
        type=int,
        default=100,
        help="frequency of tensorboard metric logging",
    )
    parser.add_argument(
        "--weights_epoch", type=int, default=10, help="save weights every x epochs"
    )
    parser.add_argument(
        "--validation_epoch",
        type=int,
        default=5,
        help="render validation every x epochs",
    )
    parser.add_argument(
        "--testset_epoch",
        type=int,
        default=300,
        help="render testset every x epochs",
    )
    parser.add_argument(
        "--video_epoch",
        type=int,
        default=300,
        help="render video every x epochs",
    )

    parser.add_argument(
        "--lrate_decay",
        type=int,
        default=250,
        help="exponential learning rate decay (in 1000s)",
    )

    parser.add_argument(
        "--envmap_path",
        type=str,
        default=None,
        help="envmap path for relighting"
    )

    parser.add_argument("--render_only", action="store_true")

    return parser


def parse_args():
    parser = add_args(
        data.add_args(
            NerdModel.add_args(
                train_utils.setup_parser(),
            ),
        ),
    )
    return train_utils.parse_args_file_without_nones(parser)

def get_envmap(path, reshape=True):
    import cv2
    img = cv2.cvtColor(
        cv2.imread(path, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB
    ).astype(np.float32)
    if reshape:
        img = cv2.resize(img, (256, 128), cv2.INTER_AREA)
    # cv2.imwrite('spotlight_gt.png', img.astype(np.uint8))

    if img.min() < 0:
        img = img + img.min()
    # img = norm_envmap(img) * 255
    # img = img / 10

    return tf.convert_to_tensor(np.clip(np.nan_to_num(img, nan=0, posinf=np.max(img), neginf=0), 0, None))

def eval_datasets(
    strategy,
    df,
    nerd,
    hwf,
    near,
    far,
    sgs_optimizer,
    steps: int,
    chunk_size: int,
    is_single_env: bool,
    envmap_path=None,
    render_poses=None,
    expname=None,
    pose_idx=None,
    fix_pose_idx=None,
):
    if not expname:
        print("No expname provided")
        exit(0)

    # Build lists to save all individual images
    gt_rgbs = []
    gt_masks = []

    align_matrix = render_poses[-1][:3, :3]
    render_poses = render_poses[:-1]

    H, W, F = render_poses[0][:3, 4]
    H, W = int(H), int(W)
    H, W, F = H // 2, W // 2, F / 2.0
    # H, W, F = H // 2, W // 2, F / 8.0
    # H, W, F = H//4, W//4, F / 4.0
    # H, W, F = int(H // 1.5), int(W // 1.5), F / 1.5


    predictions = {}
    to_extract_coarse = [("rgb", 3), ("acc_alpha", 1)]
    to_extract_fine = [
        ("rgb", 3),
        ("acc_alpha", 1),
        ("basecolor", 3),
        ("metallic", 1),
        ("roughness", 1),
        ("normal", 3),
        ("depth", 1),
    ]

    for d in df:  # Get the first illumination from test set
        img_idx, _, _, _, _, ev100_video, _, _, _ = d
        break

    illumination_context_override = None
    if envmap_path:
        illumination_context_override = np.load(envmap_path.replace('.hdr', '.npy'))
        illumination_context_override = nerd.sgs_store.validate_sgs(illumination_context_override).numpy()

        print("new context = ", illumination_context_override)
        print("new context = ", illumination_context_override.shape)
        illumination_context_override = tf.convert_to_tensor(illumination_context_override)

    pose_df = tf.data.Dataset.from_tensor_slices(render_poses[:, :3, :4])


    if envmap_path is not None:
        envmap_background = get_envmap(envmap_path, reshape=False).numpy()
        envmap_background = cv2.resize(envmap_background , (1024, 512), cv2.INTER_AREA)
        print("background = ", envmap_background.shape)
    else:
        envmap_background = None

    def norm_envmap(data):
        return np.clip(
            np.power(data / (np.ones_like(data) + data), 1.0 / 2.2),
            0,
            1
        )

    def render_pose(pose, envmap_background, envmap_rotation):
        # Always start and end with mean
        rays_o, rays_d = get_full_image_eval_grid(H, W, F, tf.reshape(pose, (3, 4)))

        _, fine_result = nerd.distributed_call(
            strategy=strategy,
            chunk_size=args.batch_size,
            ray_origins=tf.reshape(rays_o, (-1, 3)),
            ray_directions=tf.reshape(rays_d, (-1, 3)),
            camera_pose=pose,
            near_bound=0.8*near,
            far_bound=1.2*far,
            sg_illumination_idx=tf.convert_to_tensor([0]),
            ev100=ev100_video,
            training=False,
            illumination_context_override=illumination_context_override,
            high_quality=False,
        )
        # img = fine_result["rgb"].numpy()
        # img = img.reshape(H, W, 3)
        # print("raw = ", img, img.min(), img.max())
        # img = (img / img.max()) * 255
        # cv2.imwrite("temp3.png", img.astype(np.uint8))
        # exit(0)

        if envmap_background is not None:
            view_direction = math_utils.normalize(tf.reshape(rays_d, (-1, 3)))
            view_direction = tf.convert_to_tensor(view_direction.numpy() @ align_matrix @ envmap_rotation)

            uv = math_utils.direction_to_uv(tf.reshape(view_direction, (-1, 3))).numpy()
            u, v = uv[:, 0], uv[:, 1]
            x = np.clip(u * envmap_background.shape[1] - 0.5, 0, envmap_background.shape[1]).astype(np.int32)
            y = np.clip(v * envmap_background.shape[0] - 0.5, 0, envmap_background.shape[0]).astype(np.int32)
            print(x.reshape(H, W),y.reshape(H, W))

            out = np.empty((uv.shape[0], 3))
            out = envmap_background[y,x]
            out = out.reshape((H, W, 3))
            out = norm_envmap(out)

            cv2.imwrite('videos/envmap4.png', (out*255)[:, :, [2, 1, 0]].astype(np.uint8))

            view_direction = math_utils.normalize(-1 * tf.reshape(view_direction, (-1, 3)))
            fres = fine_result
            sgs = illumination_context_override

            hdr_rgb = nerd.renderer(
                sg_illuminations=sgs,
                basecolor=fres["basecolor"],
                metallic=fres["metallic"],
                roughness=fres["roughness"],
                normal=fres["normal"],
                alpha=fres["acc_alpha"],
                view_dir=view_direction,
            )

            fine_result["hdr_rgb"] = hdr_rgb

            return fine_result, out.reshape(-1, 3).astype(np.float32)
        else:
            return fine_result, None

    fine_results = {}
    hdr_name = 'estimated' if envmap_path is None else envmap_path.split('/')[-1].replace('.hdr', '')
    if fix_pose_idx is not None:
        hdr_name += '_fixed'
    out_dir = os.path.join('/export/share/projects/svbrdf/data/out_videos/nerd/', expname, hdr_name)
    # out_dir = os.path.join('videos', expname, hdr_name)
    print("saving results in : ", out_dir)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'images'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'masks'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'envmaps'), exist_ok=True)

    for iter, pose_dp in enumerate(tqdm(pose_df)):
        cur_pose = pose_dp
        print("cur pose : ", cur_pose)

        if fix_pose_idx is not None:
            envmap_rotation = np.linspace(0,360,num=720+1)[:-1][pose_idx + 360 * iter]
            envmap_rotation = Rotation.from_rotvec([0,0,envmap_rotation], degrees=True).as_matrix().astype(np.float32)
            rot4 = np.array([[0, -1, 0], [0, 0, 1], [-1, 0, 0]], dtype=np.float32).T
            envmap_rotation = np.linalg.inv(rot4) @ envmap_rotation @ rot4
        else:
            envmap_rotation = np.eye(3).astype(np.float32)

        fine_result, background = render_pose(pose_dp, envmap_background, envmap_rotation)

        if background is None:
            # fine_result["rgb"] = math_utils.linear_to_srgb(math_utils.uncharted2_filmic(fine_result["hdr_rgb"]))
            fine_result["rgb"] = math_utils.white_background_compose(
                math_utils.linear_to_srgb(math_utils.saturate(fine_result["hdr_rgb"] * math_utils.ev100_to_exp(ev100_video))),
                fine_result["acc_alpha"][..., None],
            )

        else:
            fine_result["rgb"] = math_utils.env_background_compose(
                math_utils.linear_to_srgb(
                    math_utils.uncharted2_filmic(fine_result["hdr_rgb"])
                ),
                tf.convert_to_tensor(background),
                fine_result["acc_alpha"][..., None]
            )

        rgb = (fine_result["rgb"].numpy() * 255).astype(np.uint8)
        rgb = rgb.reshape((H, W, 3))

        mask1 = fine_result["acc_alpha"][..., None]

        mask = fine_result["acc_alpha"][..., None] * (
                    tf.where(
                        fine_result["depth"] < (far * 1.2),
                        tf.ones_like(fine_result["depth"]),
                        tf.zeros_like(fine_result["depth"]),
                    )[..., None]
                )

        mask = mask.numpy().reshape((H, W)) * 255
        mask = mask.astype(np.uint8)

        mask1 = mask1.numpy().reshape((H, W)) * 255
        mask1 = mask1.astype(np.uint8)

        out_path = os.path.join(out_dir, 'images', 'rgb_' + str(pose_idx + iter*360) + '.png')
        cv2.imwrite(out_path, rgb[:, :, [2, 1, 0]])

        out_path = os.path.join(out_dir, 'masks', 'mask_' + str(pose_idx + iter*360) + '.png')
        cv2.imwrite(out_path, mask)
        cv2.imwrite(out_path.replace('mask_', 'mask_no_depth'), mask1)

        if background is not None:
            background = (background.reshape((H, W, 3)) * 255).astype(np.uint8)[:, :, [2, 1, 0]]
            out_path = os.path.join(out_dir, 'envmaps', 'env_' + str(pose_idx + iter*360) + '.png')
            cv2.imwrite(out_path, background)

    exit(0)




    # Go over validation dataset
    with strategy.scope():
        for dp in tqdm(df):
            img_idx, rays_o, rays_d, pose, mask, ev100, _, _, target = dp

            gt_rgbs.append(tf.reshape(target, (H, W, 3)))
            gt_masks.append(tf.reshape(mask, (H, W, 1)))

            # Optimize SGs first - only if we have varying illumination
            if not is_single_env:
                wb_input_value = tf.convert_to_tensor(
                    [[0.8, 0.8, 0.8]], dtype=tf.float32
                )
                strategy.run(
                    nerd.sgs_store.apply_whitebalance_to_idx,
                    (img_idx, wb_input_value, rays_o, ev100),
                )  # Start by actually ensuring the value range fits
                sgs_loss = nerd.illumination_steps(
                    rays_o,
                    rays_d,
                    pose,
                    near,
                    far,
                    img_idx,
                    ev100,
                    sgs_optimizer,
                    target,
                    steps,
                    chunk_size,
                    strategy,
                )
                print(
                    "Illumination estimation done. Remaining error:", sgs_loss.numpy()
                )

            # Render image.
            coarse_result, fine_result = nerd.distributed_call(
                strategy,
                chunk_size,
                rays_o,
                rays_d,
                pose,
                near,
                far,
                img_idx,
                ev100,
                training=False,
                illumination_context_override=illumination_context_override,
                high_quality=True,
            )

            # Extract values and reshape them to the image dimensions
            new_shape: Callable[[int], List[int]] = lambda x: [H, W, x]

            for name, channels in to_extract_coarse:
                predictions["coarse_%s" % name] = predictions.get(
                    "coarse_%s" % name, []
                ) + [tf.reshape(coarse_result[name], new_shape(channels))]

            for name, channels in to_extract_fine:
                if name in fine_result:
                    predictions["fine_%s" % name] = predictions.get(
                        "fine_%s" % name, []
                    ) + [tf.reshape(fine_result[name], new_shape(channels))]

            # Also render the environment illumination
            img_idx = img_idx[:1]  # only first needed. Others are duplications
            if illumination_context_override is None:
                sgs = nerd.sgs_store(img_idx)
            else:
                sgs = illumination_context_override

            env_map = nerd.renderer.visualize_fit((64, 128), sgs)

            predictions["fine_env_map"] = predictions.get("fine_env_map", []) + [
                env_map
            ]

    # Stack all images in dataset in batch dimension
    ret = {}
    ret["gt_rgb"] = tf.stack(gt_rgbs, 0)
    ret["gt_mask"] = tf.stack(gt_masks, 0)

    for pname, vals in predictions.items():
        ret[pname] = tf.stack(vals, 0)

    # Calculate losses
    fine_ssim = tf.reduce_mean(
        tf.image.ssim(
            math_utils.white_background_compose(ret["gt_rgb"], ret["gt_mask"]),
            math_utils.white_background_compose(ret["fine_rgb"], ret["fine_acc_alpha"]),
            max_val=1.0,
        )
    )
    fine_psnr = tf.reduce_mean(
        tf.image.psnr(
            math_utils.white_background_compose(ret["gt_rgb"], ret["gt_mask"]),
            math_utils.white_background_compose(ret["fine_rgb"], ret["fine_acc_alpha"]),
            max_val=1.0,
        )
    )

    return ret, fine_ssim, fine_psnr


def run_validation(
    strategy,
    val_df,
    nerd,
    hwf,
    near,
    far,
    sgs_optimizer,
    chunk_size: int,
    is_single_env: bool,
):
    ret, fine_ssim, fine_psnr = eval_datasets(
        strategy,
        val_df,
        nerd,
        hwf,
        near,
        far,
        sgs_optimizer,
        20,
        chunk_size,
        is_single_env,
    )

    # Log validation dataset
    horizontal_image_log("val/coarse_rgb", ret["gt_rgb"], ret["coarse_rgb"])
    horizontal_image_log("val/fine_rgb", ret["gt_rgb"], ret["fine_rgb"])

    horizontal_image_log("val/coarse_alpha", ret["gt_mask"], ret["coarse_acc_alpha"])
    horizontal_image_log("val/fine_alpha", ret["gt_mask"], ret["fine_acc_alpha"])

    for n, t in ret.items():
        filters = ["rgb", "acc_alpha"]
        if "fine" in n and not any(f in n for f in filters):
            if "normal" in n:
                tf.summary.image("val/" + n, t * 0.5 + 0.5)
            elif "env_map" in n:
                hdr_to_tb("val/env_map", t)
            else:
                tf.summary.image("val/" + n, t)

    tf.summary.scalar("val/ssim", fine_ssim)
    tf.summary.scalar("val/psnr", fine_psnr)


def main(args):
    # Setup directories, logging etc.
    with train_utils.SetupDirectory(
        args,
        copy_files=False,
        main_script=__file__,
        copy_data="data/nerd",
    ):
        strategy = (
            tf.distribute.get_strategy()
            if train_utils.get_num_gpus() <= 1
            else tf.distribute.MirroredStrategy()
        )

        # Setup dataflow
        (
            hwf,
            near,
            far,
            render_poses,
            num_images,
            _,
            train_df,
            val_df,
            test_df,
        ) = data.create_dataflow(args)

        print(f"Rendering between near {near} and far {far}")

        # Optimizer and models
        with strategy.scope():
            # Setup models
            nerd = NerdModel(num_images, args)
            lrate = train_utils.adjust_learning_rate_to_replica(args)
            if args.lrate_decay > 0:
                lrate = tf.keras.optimizers.schedules.ExponentialDecay(
                    lrate, decay_steps=args.lrate_decay * 1000, decay_rate=0.1
                )
            optimizer = tf.keras.optimizers.Adam(lrate)

            sgs_optimizer = tf.keras.optimizers.Adam(1e-3)

        # Restore if possible
        start_step = nerd.restore()
        tf.summary.experimental.set_step(start_step)

        train_dist_df = strategy.experimental_distribute_dataset(train_df)

        start_epoch = start_step // len(train_df)

        print(
            "Starting training in epoch {} at step {}".format(start_epoch, start_step)
        )

        # Will be 1 magnitude lower after advanced_loss_done steps
        advanced_loss_lambda = tf.Variable(1.0, dtype=tf.float32)
        color_loss_lambda = tf.Variable(1.0, dtype=tf.float32)
        # Run the actual optimization for x epochs

        for epoch in range(start_epoch + 1, start_epoch + 2):
            pbar = tf.keras.utils.Progbar(len(train_df))

            # Render test set when a test epoch arrives
            if True:
                print("RENDERING TESTSET...")
                ret, fine_ssim, fine_psnr = eval_datasets(
                    strategy,
                    test_df,
                    nerd,
                    hwf,
                    near,
                    far,
                    sgs_optimizer,
                    100,
                    args.batch_size,
                    args.single_env,
                    args.envmap_path,
                    render_poses,
                    args.expname,
                    args.pose_idx,
                    args.fix_pose_idx,
                )

                if args.envmap_path is None:
                    testimgdir = os.path.join(
                        args.basedir,
                        args.expname,
                        "test_imgs_{:06d}".format(tf.summary.experimental.get_step() - 1),
                    )
                else:
                    testimgdir = os.path.join(
                        args.basedir,
                        args.expname,
                        args.envmap_path.split('/')[-1].replace('.npy', '_') + "test_imgs_{:06d}".format(tf.summary.experimental.get_step() - 1),
                    )

                # testimgdir = os.path.join(
                #     args.basedir,
                #     args.expname,
                #     "test_imgs_{:06d}".format(tf.summary.experimental.get_step() - 1),
                # )

                alpha = ret["fine_acc_alpha"]
                print("Mean PSNR:", fine_psnr, "Mean SSIM:", fine_ssim)
                os.makedirs(testimgdir, exist_ok=True)
                for n, t in ret.items():
                    for b in range(t.shape[0]):
                        to_save = t[b]
                        if "normal" in n:
                            to_save = (t[b] * 0.5 + 0.5) * alpha[b] + (1 - alpha[b])

                        if "env_map" in n:
                            imageio.imwrite(
                                os.path.join(testimgdir, "{:d}_{}.png".format(b, n)),
                                to_8b(
                                    math_utils.linear_to_srgb(to_save / (1 + to_save))
                                ).numpy(),
                            )
                            imageio.imwrite(
                                os.path.join(testimgdir, "{:d}_{}.exr".format(b, n)),
                                to_save.numpy(),
                            )
                        elif "normal" in n or "depth" in n:
                            imageio.imwrite(
                                os.path.join(testimgdir, "{:d}_{}.exr".format(b, n)),
                                to_save.numpy(),
                            )
                            if "normal" in n:
                                imageio.imwrite(
                                    os.path.join(
                                        testimgdir, "{:d}_{}.png".format(b, n)
                                    ),
                                    to_8b(to_save).numpy(),
                                )
                        else:
                            imageio.imwrite(
                                os.path.join(testimgdir, "{:d}_{}.png".format(b, n)),
                                to_8b(to_save).numpy(),
                            )

            # Render video when a video epoch arrives
            if False:
                print("RENDERING VIDEO...")
                video_dir = os.path.join(
                    args.basedir,
                    args.expname,
                    "video_{:06d}".format(tf.summary.experimental.get_step()),
                )
                video_img_dir = os.path.join(
                    video_dir,
                    "images",
                )
                os.makedirs(video_img_dir, exist_ok=True)

                render_video(
                    hwf,
                    test_df,
                    render_poses,
                    strategy,
                    near,
                    far,
                    nerd,
                    args,
                    video_img_dir,
                    video_dir,
                )

            if args.render_only:
                return


def render_video(
    hwf,
    test_df,
    render_poses,
    strategy,
    near,
    far,
    nerd,
    args,
    video_img_dir,
    video_dir,
):
    H, W, F = hwf
    fine_results = {}

    options = tf.data.Options()
    options.experimental_distribute.auto_shard_policy = (
        tf.data.experimental.AutoShardPolicy.DATA
    )

    # switch between illuminations
    num_illuminations = 6 + 2  # Start and end with same latent
    num_seconds = 6
    num_fps = 30

    for d in test_df:  # Get the first illumination from test set
        img_idx, _, _, _, _, ev100_video, _, _, _ = d

        break

    pose_df = tf.data.Dataset.from_tensor_slices(render_poses[:, :3, :4])

    def render_pose(pose):
        rays_o, rays_d = get_full_image_eval_grid(H, W, F, tf.reshape(pose, (3, 4)))

        _, fine_result = nerd.distributed_call(
            strategy=strategy,
            chunk_size=args.batch_size,
            ray_origins=tf.reshape(rays_o, (-1, 3)),
            ray_directions=tf.reshape(rays_d, (-1, 3)),
            camera_pose=pose,
            near_bound=near,
            far_bound=far,
            sg_illumination_idx=img_idx,
            ev100=ev100_video,
            training=False,
        )

        return fine_result

    for pose_dp in tqdm(pose_df):
        cur_pose = pose_dp

        fine_result = render_pose(pose_dp)

        fine_result["rgb"] = math_utils.white_background_compose(
            math_utils.linear_to_srgb(
                math_utils.uncharted2_filmic(fine_result["hdr_rgb"])
            ),
            fine_result["acc_alpha"][..., None]
            * (
                tf.where(
                    fine_result["depth"] < (far * 0.9),
                    tf.ones_like(fine_result["depth"]),
                    tf.zeros_like(fine_result["depth"]),
                )[..., None]
            ),
        )

        for k, v in fine_result.items():
            fine_results[k] = fine_results.get(k, []) + [v.numpy()]

    total_frames = num_seconds * num_fps
    frames_per_illumination = total_frames // (num_illuminations - 1)
    total_frames = frames_per_illumination * (
        num_illuminations - 1
    )  # Make sure that everything fits

    illuminations_path = "data/nerd/video_sgs"
    illuminations = [
        np.load(os.path.join(illuminations_path, f))[None, ...]
        for f in os.listdir(illuminations_path)
    ]

    # Always start and end with main video SGs
    main_video_sgs = nerd.sgs_store(img_idx).numpy()
    illuminations = [main_video_sgs] + illuminations + [main_video_sgs]

    frame_sgs = []
    frame_env_idx = 0
    imageio.plugins.freeimage.download()

    env_maps = []

    for sgs0, sgs1 in zip(illuminations, illuminations[1:]):
        for frame in range(frames_per_illumination):
            blend_alpha = frame / (frames_per_illumination - 1)
            cur_sgs = nerd.sgs_store.validate_sgs(
                sgs0 * (1 - blend_alpha) + sgs1 * blend_alpha
            ).numpy()

            frame_sgs.append(cur_sgs)

            env_map = nerd.renderer.visualize_fit((128, 256), cur_sgs)
            env_maps.append(env_map.numpy())

            imageio.imwrite(
                os.path.join(video_img_dir, "env_{:06d}.exr".format(frame_env_idx)),
                env_map.numpy()[0],
            )
            frame_env_idx += 1

    number_of_sgs_frames = len(frame_sgs)
    # pad frame latents if required
    div_remain = np.ceil(number_of_sgs_frames / train_utils.get_num_gpus())
    mod_remain = int((div_remain * train_utils.get_num_gpus()) - number_of_sgs_frames)
    for _ in range(mod_remain):
        frame_sgs.append(frame_sgs[-1])  # Clone last

    frame_sgs_pad = np.concatenate(frame_sgs, 0)
    print(
        frame_sgs_pad.shape,
        number_of_sgs_frames,
        mod_remain,
        train_utils.get_num_gpus(),
    )

    sgs_df = (
        tf.data.Dataset.from_tensor_slices(
            tf.convert_to_tensor(frame_sgs_pad, dtype=tf.float32)
        )
        .batch(train_utils.get_num_gpus())
        .with_options(options)
    )
    sgs_dist_df = strategy.experimental_distribute_dataset(sgs_df)

    # Render all sgs
    with strategy.scope():
        # Use last pose
        rays_o, rays_d = get_full_image_eval_grid(H, W, F, tf.reshape(cur_pose, (3, 4)))

        def render_sgs(rays_o, rays_d, fres, sgs):
            tf.debugging.assert_shapes(
                [
                    (rays_o, (H, W, 3)),
                    (rays_d, (H, W, 3)),
                    (
                        sgs,
                        (1, 24, 7),
                    ),
                ]
            )

            view_direction = math_utils.normalize(-1 * tf.reshape(rays_d, (-1, 3)))

            hdr_rgb = nerd.renderer(
                sg_illuminations=sgs,
                basecolor=fres["basecolor"],
                metallic=fres["metallic"],
                roughness=fres["roughness"],
                normal=fres["normal"],
                alpha=fres["acc_alpha"],
                view_dir=view_direction,
            )

            rgb = math_utils.white_background_compose(
                math_utils.linear_to_srgb(math_utils.uncharted2_filmic(hdr_rgb)),
                fres["acc_alpha"][..., None],
            )

            return rgb

        for sgs_dp in tqdm(sgs_dist_df):
            rgb_per_replica = strategy.run(
                render_sgs, (rays_o, rays_d, fine_result, sgs_dp)
            )
            rgb_result = strategy.gather(rgb_per_replica, 0).numpy()
            rgb_results = np.split(rgb_result, train_utils.get_num_gpus(), 0)
            fine_results["rgb"] = fine_results.get("rgb", []) + rgb_results

    # Everything is now a numpy
    fine_result_np = {
        k: np.stack(v, 0)[: render_poses.shape[0] + number_of_sgs_frames]
        for k, v in fine_results.items()
    }
    # reshape and extract
    rgb = fine_result_np["rgb"]
    rgb = rgb.reshape((-1, H, W, 3))

    # save individual images and video
    imageio.mimwrite(
        os.path.join(video_dir, "rgb.mp4"),
        (rgb * 255).astype(np.uint8),
        fps=30,
        quality=8,
    )

    for i in range(rgb.shape[0]):
        imageio.imwrite(
            os.path.join(video_img_dir, "rgb_{:06d}.png".format(i)),
            (rgb[i] * 255).astype(np.uint8),
        )

    alpha = fine_result_np["acc_alpha"].reshape((-1, H, W, 1))
    parameters = {}
    parameters["basecolor"] = math_utils.linear_to_srgb(
        (fine_result_np["basecolor"].reshape((-1, H, W, 3)) * alpha) + (1 - alpha)
    ).numpy()
    parameters["metallic"] = math_utils.linear_to_srgb(
        (fine_result_np["metallic"].reshape((-1, H, W, 1)) * alpha) + (1 - alpha)
    ).numpy()
    parameters["roughness"] = (
        fine_result_np["roughness"].reshape((-1, H, W, 1)) * alpha
    ) + (1 - alpha)
    parameters["normal"] = math_utils.linear_to_srgb(
        ((fine_result_np["normal"].reshape((-1, H, W, 3)) * 0.5 + 0.5) * alpha)
        + (1 - alpha)
    ).numpy()

    for n, imgs in parameters.items():
        imageio.mimwrite(
            os.path.join(video_dir, "{}.mp4".format(n)),
            (imgs * 255).astype(np.uint8),
            fps=30,
            quality=8,
        )

        for i in range(imgs.shape[0]):
            imageio.imwrite(
                os.path.join(video_img_dir, "{}_{:06d}.png".format(n, i)),
                (imgs[i] * 255).astype(np.uint8),
            )


def render_test_example(dp, hwf, nerd, near, far, strategy):
    (
        img_idx,
        _,
        _,
        pose,
        _,
        ev100,
        _,
        _,
        _,
    ) = dp

    H, W, F = hwf
    rays_o, rays_d = get_full_image_eval_grid(H, W, F, pose[0])

    coarse_result, fine_result = nerd.distributed_call(
        strategy=strategy,
        chunk_size=1024,
        ray_origins=tf.reshape(rays_o, (-1, 3)),
        ray_directions=tf.reshape(rays_d, (-1, 3)),
        camera_pose=pose,
        near_bound=near,
        far_bound=far,
        sg_illumination_idx=img_idx,
        ev100=ev100,
        training=False,
        high_quality=True,
    )

    horizontal_image_log(
        "train/rgb",
        tf.reshape(coarse_result["rgb"], (1, H, W, 3)),
        tf.reshape(fine_result["rgb"], (1, H, W, 3)),
    )
    horizontal_image_log(
        "train/alpha",
        tf.reshape(coarse_result["acc_alpha"], (1, H, W, 1)),
        tf.reshape(fine_result["acc_alpha"], (1, H, W, 1)),
    )

    for n, t in fine_result.items():
        filters = ["rgb", "alpha"]
        if not any(f in n for f in filters):
            if "normal" in n:
                tf.summary.image("train/" + n, tf.reshape(t * 0.5 + 0.5, (1, H, W, 3)))
            elif "brdf_embedding" in n:
                min_val = tf.reduce_min(t)
                max_val = tf.reduce_max(t)
                t_scaled = (t - min_val) / (max_val - min_val)

                pad = 3 - t.shape[-1]
                t_pad = tf.concat(
                    [
                        t_scaled,
                        math_utils.repeat(tf.zeros_like(t_scaled[..., :1]), pad, -1),
                    ],
                    -1,
                )

                t_mask = tf.reshape(t_pad, (1, H, W, 3)) * tf.reshape(
                    fine_result["acc_alpha"], (1, H, W, 1)
                )

                tf.summary.image("train/" + n, t_mask)
            else:
                if len(t.shape) == 1:
                    t = t[:, None]
                tf.summary.image("train/" + n, tf.reshape(t, (1, H, W, t.shape[-1])))

    sgs = nerd.sgs_store(img_idx)
    env_map = nerd.renderer.visualize_fit((64, 128), sgs)
    hdr_to_tb("train/env_map", env_map[None, :])


if __name__ == "__main__":
    args = parse_args()
    print(args)

    main(args)
