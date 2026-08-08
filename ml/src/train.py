
"""
Training pipeline for the project-category image classifier.

Transfer learning on ResNet-18 (pretrained on ImageNet): early layers
frozen (already encode general visual features), later layers +
a new classification head fine-tuned on our 8 categories.
"""
import json
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms, models
from PIL import Image

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 32
NUM_EPOCHS = 15
LEARNING_RATE = 0.001
VAL_SPLIT = 0.2

# Standard ImageNet normalization — required when using a pretrained
# model, since it was trained on images normalized this way.
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

val_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


class ProjectImageDataset(Dataset):
    """Loads images from data/raw/<category>/*.jpg, using folder names
    as labels."""

    def __init__(self, samples: list[tuple[Path, int]], transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        return self.transform(image), label


def build_datasets():
    categories = sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])
    class_to_idx = {cat: i for i, cat in enumerate(categories)}

    all_samples = []
    for category in categories:
        image_paths = sorted((DATA_DIR / category).glob("*.jpg"))
        for path in image_paths:
            all_samples.append((path, class_to_idx[category]))

    print(f"Found {len(all_samples)} images across {len(categories)} categories:")
    for category in categories:
        count = sum(1 for _, label in all_samples if label == class_to_idx[category])
        print(f"  {category}: {count}")

    # Split indices first, then apply different transforms to train/val —
    # random_split alone can't do this since it shares the underlying
    # dataset object, so we build two dataset instances over the same
    # split indices instead.
    val_size = int(len(all_samples) * VAL_SPLIT)
    train_size = len(all_samples) - val_size
    train_samples, val_samples = random_split(all_samples, [train_size, val_size])

    train_dataset = ProjectImageDataset([all_samples[i] for i in train_samples.indices], train_transform)
    val_dataset = ProjectImageDataset([all_samples[i] for i in val_samples.indices], val_transform)

    return train_dataset, val_dataset, class_to_idx

def build_model(num_classes: int) -> nn.Module:
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)

    # Freeze all pretrained layers first — they already encode general
    # visual features (edges, textures, shapes) learned from ImageNet's
    # millions of images, which a dataset of a few hundred images per
    # category could never learn from scratch as well.
    for param in model.parameters():
        param.requires_grad = False

    # Unfreeze the last residual block (layer4) so the model can adapt
    # its higher-level, more task-specific features to our categories,
    # while keeping the earlier, more general layers frozen.
    for param in model.layer4.parameters():
        param.requires_grad = True

    # Replace the final classification head — the pretrained model
    # outputs 1000 ImageNet classes; we need 8.
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(model.fc.in_features, num_classes),
    )

    return model.to(DEVICE)


def compute_class_weights(train_dataset, class_to_idx) -> torch.Tensor:
    """Weights the loss function inversely proportional to class
    frequency, so underrepresented categories (likely, given uneven
    search-result availability) aren't systematically ignored by the
    model in favor of overrepresented ones."""
    counts = torch.zeros(len(class_to_idx))
    for _, label in train_dataset.samples:
        counts[label] += 1

    counts = torch.clamp(counts, min=1)  # avoid divide-by-zero for empty classes
    weights = 1.0 / counts
    weights = weights / weights.sum() * len(class_to_idx)  # normalize
    return weights.to(DEVICE)


def train_one_epoch(model, loader, optimizer, criterion) -> float:
    model.train()
    total_loss = 0.0
    for images, labels in loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)

    return total_loss / len(loader.dataset)


def train_model(model, train_loader, val_loader, class_weights):
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    # Only optimize parameters that are actually unfrozen (layer4 + fc) —
    # passing frozen parameters to the optimizer wastes memory and,
    # depending on optimizer internals, can cause subtle bugs.
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(trainable_params, lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=3)

    history = {"train_loss": [], "val_accuracy": []}
    best_val_accuracy = 0.0

    for epoch in range(NUM_EPOCHS):
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion)
        val_accuracy, _, _ = evaluate(model, val_loader)
        scheduler.step(val_accuracy)

        history["train_loss"].append(train_loss)
        history["val_accuracy"].append(val_accuracy)

        print(f"Epoch {epoch+1}/{NUM_EPOCHS} — train_loss: {train_loss:.4f}, val_accuracy: {val_accuracy:.4f}")

        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            torch.save(model.state_dict(), CHECKPOINT_DIR / "best_model.pt")
            print(f"  New best model saved (val_accuracy: {val_accuracy:.4f})")

    return history

from sklearn.metrics import precision_recall_fscore_support


def evaluate(model, loader):
    """Returns (accuracy, all_predictions, all_labels) — the raw
    predictions/labels are returned so the caller can compute
    per-class precision/recall/F1 without a second pass over the data."""
    model.eval()
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)

            correct += (predicted == labels).sum().item()
            total += labels.size(0)
            all_preds.extend(predicted.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    accuracy = correct / total if total > 0 else 0.0
    return accuracy, all_preds, all_labels


def main():
    train_dataset, val_dataset, class_to_idx = build_datasets()
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    model = build_model(num_classes=len(class_to_idx))
    class_weights = compute_class_weights(train_dataset, class_to_idx)

    print(f"\nTraining on {DEVICE} — {len(train_dataset)} train / {len(val_dataset)} val images\n")
    history = train_model(model, train_loader, val_loader, class_weights)

    # Load the best checkpoint (not necessarily the last epoch) for
    # final evaluation and metric reporting.
    model.load_state_dict(torch.load(CHECKPOINT_DIR / "best_model.pt"))
    final_accuracy, preds, labels = evaluate(model, val_loader)

    precision, recall, f1, support = precision_recall_fscore_support(
        labels, preds, labels=list(range(len(class_to_idx))), zero_division=0
    )

    print(f"\nFinal validation accuracy: {final_accuracy:.4f}\n")
    print("Per-class metrics:")
    print(f"{'Category':<15} {'Precision':<10} {'Recall':<10} {'F1':<10} {'Support':<8}")
    for i, category in idx_to_class.items():
        print(f"{category:<15} {precision[i]:<10.3f} {recall[i]:<10.3f} {f1[i]:<10.3f} {support[i]:<8}")

    # Save everything needed to reproduce/report on this training run.
    results = {
        "final_val_accuracy": final_accuracy,
        "class_to_idx": class_to_idx,
        "history": history,
        "per_class_metrics": {
            idx_to_class[i]: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i in range(len(class_to_idx))
        },
    }
    with open(CHECKPOINT_DIR / "training_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nModel and results saved to {CHECKPOINT_DIR}/")


if __name__ == "__main__":
    main()
