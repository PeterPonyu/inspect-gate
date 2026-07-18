#!/usr/bin/env python3
"""TIER 2 latency: Dinomaly (DINOv2-base backbone) per-image GPU inference.

Loads the branch-A VisA Dinomaly checkpoint (seed 0) into the reference
ViTill architecture and runs REAL eval-mode inference on real VisA images,
measuring:

  * batch=1, deployment-realistic per-image latency: median + p95 over the
    full forward + anomaly-map + image-score aggregation, CUDA-synchronized
    per image (i.e. the whole decision-producing pass, not just the encoder).
  * throughput at a larger batch (images/s), the offline/batched regime.

Every number is MEASURED on the recorded GPU. Architecture/transforms are
taken verbatim from the reference repo (dinomaly_visa_uni.py: image 448,
crop 392, dinov2reg_vit_base_14, target layers 2-9, 8-block decoder). The
DINOv2 pretrained download in vit_encoder.load is bypassed -- the encoder
is constructed directly and then FULLY overwritten by the checkpoint's
encoder.* weights (verified by load_state_dict strict=True).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

DINOMALY_REPO = Path(
    "/tmp/claude-1000/-home-zeyufu-Desktop-ml-reliability-research/"
    "4bb1ca63-4f34-4dd0-abbc-323c01490703/scratchpad/Dinomaly"
)
sys.path.insert(0, str(DINOMALY_REPO))

from dinov2.models import vision_transformer as vit_dinov2  # noqa: E402
from models.uad import ViTill  # noqa: E402
from models.vision_transformer import Block as VitBlock, bMlp, LinearAttention2  # noqa: E402
from utils import cal_anomaly_maps, get_gaussian_kernel  # noqa: E402

HERE = Path(__file__).resolve().parent
CKPT = Path(
    "/home/zeyufu/Desktop/ml-reliability-research/orchestration_2026-07-12/"
    "visa_pull/root/autodl-tmp/visa_brancha/dinomaly/seed_0/run/model.pth"
)
IMG_DIR = Path(
    "/tmp/claude-1000/-home-zeyufu-Desktop-ml-reliability-research/"
    "4bb1ca63-4f34-4dd0-abbc-323c01490703/scratchpad/visa_imgs/candle/Data/Images"
)

IMAGE_SIZE = 448
CROP_SIZE = 392
MAX_RATIO = 0.01     # image-score aggregation used in the paper's eval
RESIZE_MASK = 256


def build_model(device):
    encoder = vit_dinov2.vit_base(
        patch_size=14, img_size=518, block_chunks=0, init_values=1e-8,
        num_register_tokens=4, interpolate_antialias=False, interpolate_offset=0.1,
    )
    embed_dim, num_heads = 768, 12
    bottleneck = nn.ModuleList([bMlp(embed_dim, embed_dim * 4, embed_dim, drop=0.2)])
    decoder = nn.ModuleList([
        VitBlock(dim=embed_dim, num_heads=num_heads, mlp_ratio=4., qkv_bias=True,
                 norm_layer=partial(nn.LayerNorm, eps=1e-8), attn_drop=0.,
                 attn=LinearAttention2)
        for _ in range(8)
    ])
    model = ViTill(
        encoder=encoder, bottleneck=bottleneck, decoder=decoder,
        target_layers=[2, 3, 4, 5, 6, 7, 8, 9], mask_neighbor_size=0,
        fuse_layer_encoder=[[0, 1, 2, 3], [4, 5, 6, 7]],
        fuse_layer_decoder=[[0, 1, 2, 3], [4, 5, 6, 7]],
    )
    state = torch.load(CKPT, map_location="cpu", weights_only=False)
    missing, unexpected = model.load_state_dict(state, strict=True)
    assert not missing and not unexpected, (missing, unexpected)
    return model.to(device).eval()


def score_batch(model, gaussian_kernel, img):
    """Full decision pass: forward -> anomaly map -> per-image score
    (max_ratio top-fraction mean), exactly the paper's eval path."""
    en, de = model(img)
    anomaly_map, _ = cal_anomaly_maps(en, de, img.shape[-1])
    anomaly_map = F.interpolate(anomaly_map, size=RESIZE_MASK, mode="bilinear", align_corners=False)
    anomaly_map = gaussian_kernel(anomaly_map)
    flat = anomaly_map.flatten(1)
    k = int(flat.shape[1] * MAX_RATIO)
    sp = torch.sort(flat, dim=1, descending=True)[0][:, :k].mean(dim=1)
    return sp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-images", type=int, default=250)
    ap.add_argument("--batch-throughput", type=int, default=32)
    args = ap.parse_args()

    assert torch.cuda.is_available(), "no CUDA"
    device = "cuda:0"
    gpu_name = torch.cuda.get_device_name(0)
    torch.backends.cudnn.benchmark = True

    tfm = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.CenterCrop(CROP_SIZE),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    paths = sorted([p for p in IMG_DIR.rglob("*") if p.suffix.lower() in (".jpg", ".png", ".jpeg")])
    paths = paths[: args.n_images]
    assert len(paths) >= 200, f"need >=200 imgs, got {len(paths)}"
    tensors = [tfm(Image.open(p).convert("RGB")) for p in paths]
    n = len(tensors)

    model = build_model(device)
    gk = get_gaussian_kernel(kernel_size=5, sigma=4).to(device)

    # Preload all tensors to GPU so we time COMPUTE, not host->device copy of
    # the whole set (a single-image H2D copy is included in batch=1 timing).
    gpu_imgs = [t.unsqueeze(0).to(device) for t in tensors]

    # --- warmup ---
    with torch.no_grad():
        for i in range(10):
            _ = score_batch(model, gk, gpu_imgs[i % n])
        torch.cuda.synchronize()

    # --- batch=1 per-image latency (CUDA-synced per image) ---
    per_image_ms = []
    with torch.no_grad():
        for t in gpu_imgs:
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            _ = score_batch(model, gk, t)
            torch.cuda.synchronize()
            per_image_ms.append(1000.0 * (time.perf_counter() - t0))
    arr = np.asarray(per_image_ms)

    # --- throughput at larger batch ---
    B = args.batch_throughput
    batch = torch.cat(gpu_imgs[:B], dim=0)
    with torch.no_grad():
        for _ in range(3):
            _ = score_batch(model, gk, batch)
        torch.cuda.synchronize()
        n_rep = 10
        t0 = time.perf_counter()
        for _ in range(n_rep):
            _ = score_batch(model, gk, batch)
        torch.cuda.synchronize()
        batch_total_s = time.perf_counter() - t0
    throughput_ips = (n_rep * B) / batch_total_s
    batch_per_image_ms = 1000.0 * batch_total_s / (n_rep * B)

    peak_mem_gb = torch.cuda.max_memory_allocated() / (1024 ** 3)
    nparams = sum(p.numel() for p in model.parameters())

    out = {
        "measured": True,
        "date": "2026-07-13",
        "gpu": gpu_name,
        "torch": torch.__version__,
        "backbone": "Dinomaly (DINOv2-base ViT, reg4, patch14)",
        "checkpoint": str(CKPT),
        "checkpoint_setting": "VisA branch-A unified, seed 0",
        "images": {
            "source": "VisA candle test images",
            "n_images": n,
            "image_size": IMAGE_SIZE,
            "crop_size": CROP_SIZE,
            "score_aggregation": f"top-{MAX_RATIO} mean of gaussian-smoothed anomaly map, resize_mask={RESIZE_MASK}",
        },
        "n_params_millions": round(nparams / 1e6, 2),
        "peak_gpu_mem_gb": round(peak_mem_gb, 3),
        "batch1_per_image_latency_ms": {
            "n": int(arr.size),
            "median": float(np.median(arr)),
            "mean": float(np.mean(arr)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "std": float(np.std(arr, ddof=1)),
        },
        "batch1_throughput_ips": 1000.0 / float(np.median(arr)),
        "batched_throughput": {
            "batch_size": B,
            "images_per_second": throughput_ips,
            "amortized_ms_per_image": batch_per_image_ms,
            "n_batch_repeats": n_rep,
        },
    }
    (HERE / "dinomaly_latency.json").write_text(json.dumps(out, indent=2))

    print(f"GPU: {gpu_name} | torch {torch.__version__}")
    print(f"params: {out['n_params_millions']}M | peak mem: {out['peak_gpu_mem_gb']} GB")
    print(f"batch=1 per-image: median={out['batch1_per_image_latency_ms']['median']:.2f} ms "
          f"p95={out['batch1_per_image_latency_ms']['p95']:.2f} ms "
          f"({out['batch1_throughput_ips']:.1f} img/s)  n={n}")
    print(f"batch={B}: {throughput_ips:.1f} img/s ({batch_per_image_ms:.2f} ms/img amortized)")
    print(f"wrote {HERE / 'dinomaly_latency.json'}")


if __name__ == "__main__":
    main()
