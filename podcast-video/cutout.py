import sys, numpy as np, cv2, mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

MODEL = sys.argv[1]; src = sys.argv[2]; out = sys.argv[3]
img = cv2.cvtColor(cv2.imread(src), cv2.COLOR_BGR2RGB) if not src.endswith('.webp') else None
if img is None:
    from PIL import Image
    img = np.array(Image.open(src).convert('RGB'))
H0, W0 = img.shape[:2]
# work at ~1800px tall
s = 1800 / H0
img = cv2.resize(img, (int(W0 * s), 1800), interpolation=cv2.INTER_AREA)
H, W = img.shape[:2]

seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=mpt.BaseOptions(model_asset_path=MODEL), output_confidence_masks=True))
res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img)))
bg = res.confidence_masks[0].numpy_view()
p = 1 - cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR)

# grabcut refinement in the uncertain band
gc = np.full((H, W), cv2.GC_PR_BGD, np.uint8)
gc[p > 0.5] = cv2.GC_PR_FGD
k = np.ones((15, 15), np.uint8)
gc[cv2.erode((p > 0.92).astype(np.uint8), k, iterations=2) > 0] = cv2.GC_FGD
gc[cv2.dilate((p > 0.08).astype(np.uint8), k, iterations=2) == 0] = cv2.GC_BGD
bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
small = 0.5
gcs = cv2.resize(gc, None, fx=small, fy=small, interpolation=cv2.INTER_NEAREST)
ims = cv2.resize(img, None, fx=small, fy=small, interpolation=cv2.INTER_AREA)
cv2.grabCut(cv2.cvtColor(ims, cv2.COLOR_RGB2BGR), gcs, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
m = np.where((gcs == cv2.GC_FGD) | (gcs == cv2.GC_PR_FGD), 1.0, 0.0).astype(np.float32)
m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
# keep largest component
n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0.5).astype(np.uint8))
if n > 1:
    big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    keep = (lab == big).astype(np.float32)
    keep = cv2.dilate(keep, np.ones((5, 5), np.uint8))
    m *= keep
alpha = cv2.GaussianBlur(m, (0, 0), 1.6)
alpha = np.clip((alpha - 0.08) / 0.84, 0, 1)

# despill blue at the edges + gentle warm grade
f = img.astype(np.float32) / 255
edge = (alpha > 0.01) & (alpha < 0.98)
edge = cv2.dilate(edge.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
r, g, b = f[..., 0], f[..., 1], f[..., 2]
cap = np.maximum(r, g) * 1.02
b2 = np.where(edge & (b > cap), cap, b)
f = np.stack([r, g, b2], -1)
f[..., 0] *= 1.035; f[..., 2] *= 0.955
f = np.clip((f - 0.5) * 1.06 + 0.5 - 0.01, 0, 1)
rgba = np.dstack([f, alpha])
# crop to content
ys, xs = np.where(alpha > 0.02)
y0, y1 = max(0, ys.min() - 20), H
x0, x1 = max(0, xs.min() - 20), min(W, xs.max() + 20)
rgba = rgba[y0:y1, x0:x1]
cv2.imwrite(out, cv2.cvtColor((rgba * 255).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
print(out, rgba.shape, 'crop', (x0, y0, x1, y1), 'of', (W, H))
