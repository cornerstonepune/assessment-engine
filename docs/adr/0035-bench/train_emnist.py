"""A standard small CNN (two conv layers, the PyTorch MNIST example's shape) trained on EMNIST-digits (240k train,
40k test) — nothing from our papers. Saves emnist_cnn.pt."""
import gzip, numpy as np, torch, torch.nn as nn, torch.nn.functional as F
def idx(p, img):
    b = gzip.open(p).read()
    return np.frombuffer(b, np.uint8, offset=16).reshape(-1, 28, 28) if img else np.frombuffer(b, np.uint8, offset=8)
g = "emnist/gzip/emnist-digits-"
X = idx(g + "train-images-idx3-ubyte.gz", 1).transpose(0, 2, 1); Y = idx(g + "train-labels-idx1-ubyte.gz", 0)
Xt = idx(g + "test-images-idx3-ubyte.gz", 1).transpose(0, 2, 1); Yt = idx(g + "test-labels-idx1-ubyte.gz", 0)
class Net(nn.Module):
    def __init__(s):
        super().__init__(); s.c1 = nn.Conv2d(1, 32, 3); s.c2 = nn.Conv2d(32, 64, 3); s.d = nn.Dropout(0.25); s.f1 = nn.Linear(9216, 128); s.f2 = nn.Linear(128, 10)
    def forward(s, x):
        x = F.max_pool2d(F.relu(s.c2(F.relu(s.c1(x)))), 2); x = s.d(torch.flatten(x, 1)); return s.f2(F.relu(s.f1(x)))
torch.manual_seed(0); net = Net(); opt = torch.optim.Adam(net.parameters(), 1e-3)
T = lambda a: (torch.tensor(a, dtype=torch.float32).unsqueeze(1) / 255 - 0.1307) / 0.3081
Xtr, Ytr = T(X), torch.tensor(Y, dtype=torch.long)
for ep in range(2):
    perm = torch.randperm(len(Xtr)); net.train()
    for i in range(0, len(perm), 256):
        b = perm[i:i + 256]; opt.zero_grad(); F.cross_entropy(net(Xtr[b]), Ytr[b]).backward(); opt.step()
    net.eval()
    XT = T(Xt)
    with torch.no_grad(): pred = torch.cat([net(XT[i:i+2000]).argmax(1) for i in range(0, len(XT), 2000)]).numpy()
    acc = (pred == Yt).mean()
    print("epoch", ep, "EMNIST test acc", round(float(acc), 4), flush=True)
torch.save(net.state_dict(), "emnist_cnn.pt")
