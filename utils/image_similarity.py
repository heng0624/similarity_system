from PIL import Image
import torch
import torch.nn.functional as F
from torchvision import models, transforms

# ---------------------------------------
# Load ResNet50 (PyTorch version)
# ---------------------------------------
img_model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
img_model = torch.nn.Sequential(*list(img_model.children())[:-1])  # remove classifier
img_model.eval()

# ---------------------------------------
# Preprocess pipeline
# ---------------------------------------
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std =[0.229, 0.224, 0.225]
    )
])

# ---------------------------------------
# Extract embedding
# ---------------------------------------
def get_image_embedding(path):
    img = Image.open(path).convert("RGB")
    img = preprocess(img).unsqueeze(0)

    with torch.no_grad():
        emb = img_model(img).squeeze()  # shape: (2048,)
    return emb

# ---------------------------------------
# Compute cosine similarity
# ---------------------------------------
def compute_image_similarity(f1, f2):
    emb1 = get_image_embedding(f1)
    emb2 = get_image_embedding(f2)

    sim = F.cosine_similarity(emb1, emb2, dim=0).item()
    # normalize 0–1 range
    sim = max(0, min(sim, 1))
    return sim * 100
