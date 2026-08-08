
"""
Image classification inference wrapper.

Loads the trained ResNet-18 model once at import time (not per-request)
and exposes a simple classify_image() function. Mirrors the same
preprocessing used during training's validation pipeline — using
different preprocessing at inference time than at training time is a
classic source of silently degraded accuracy.
"""
import io
import json
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "best_model.pt"
CLASS_MAP_PATH = ARTIFACTS_DIR / "class_to_idx.json"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Identical to train.py's val_transform — deliberately not augmented
# (no random crop/flip/jitter), since inference should be deterministic.
inference_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


def _load_class_mapping() -> dict[int, str]:
    with open(CLASS_MAP_PATH) as f:
        class_to_idx = json.load(f)
    return {v: k for k, v in class_to_idx.items()}


def _load_model(num_classes: int) -> nn.Module:
    model = models.resnet18(weights=None)  # no pretrained weights — we're loading our own
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(model.fc.in_features, num_classes),
    )
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.to(DEVICE)
    model.eval()
    return model


# Loaded once at module import time, reused across every request.
_idx_to_class = _load_class_mapping()
_model = _load_model(num_classes=len(_idx_to_class))


def classify_image(image_bytes: bytes) -> tuple[str, float]:
    """Returns (predicted_category, confidence) for a single image."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = inference_transform(image).unsqueeze(0).to(DEVICE)  # add batch dimension

    with torch.no_grad():
        outputs = _model(tensor)
        probabilities = torch.softmax(outputs, dim=1)
        confidence, predicted_idx = torch.max(probabilities, dim=1)

    category = _idx_to_class[predicted_idx.item()]
    return category, confidence.item()
    