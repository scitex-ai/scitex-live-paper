#!/usr/bin/env python3
"""Build the ``example-project-mnist`` seed bundle (operator standing orders).

Generates a small, fully computed MNIST-classification demo bundle:

  examples/example-project-mnist/
    manuscript.pdf   # 3-page demo paper (matplotlib): summary, digit
                     # samples (real MNIST images), accuracy figure
    claims.json      # scitex-clew.claims/v1: 3 claims carrying the
                     # COMPUTED test accuracies (never hand-typed)
    dag.mmd          # fetch -> split -> train -> evaluate -> render
    provenance.yaml  # scitex-clew.provenance/v1: dataset, script,
                     # versions, seeds
    figz/            # mnist_accuracy.png + mnist_digits.png (also
                     # embedded in the manuscript)
    README.md        # what this is + how to regenerate

Reproducibility: fixed seeds, pinned dataset (OpenML ``mnist_784`` v1),
versions recorded in ``provenance.yaml``. Requires ``scikit-learn``,
``matplotlib``, ``numpy`` (example-only deps — the test suite never
imports this script).

Status values stay ``registered``: these are example claims for UI
development, not verified research findings.

Hub side drops this directory into the ``example-project-mnist`` user
project; ``/apps/live-paper/?working_dir=<bundle>`` then renders it.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "example-project-mnist"

N_TRAIN = 10_000
N_TEST = 2_000
SEED = 0
KNN_K = 5
KNN_TRAIN = 2_000  # kNN keeps a small reference set so it stays fast

PAGE_W_PT, PAGE_H_PT = 612.0, 792.0  # US Letter


def _utcnow() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_mnist():
    """Real MNIST pixels via OpenML (cached under ~/.cache)."""
    from sklearn.datasets import fetch_openml

    mnist = fetch_openml("mnist_784", version=1, parser="auto")
    X = np.asarray(mnist.data, dtype=np.float64) / 255.0
    y = np.asarray(mnist.target, dtype=int)
    return X, y


def split(X, y):
    rng = np.random.RandomState(SEED)
    idx = rng.permutation(len(X))
    X, y = X[idx], y[idx]
    return X[:N_TRAIN], y[:N_TRAIN], X[N_TRAIN : N_TRAIN + N_TEST], y[N_TRAIN : N_TRAIN + N_TEST]


def train_logreg(X_train, y_train):
    from sklearn.linear_model import LogisticRegression

    clf = LogisticRegression(max_iter=1000, random_state=SEED)
    clf.fit(X_train, y_train)
    return clf


def train_knn(X_train, y_train):
    from sklearn.neighbors import KNeighborsClassifier

    clf = KNeighborsClassifier(n_neighbors=KNN_K)
    clf.fit(X_train[:KNN_TRAIN], y_train[:KNN_TRAIN])
    return clf


def accuracy(clf, X_test, y_test) -> float:
    return float(clf.score(X_test, y_test))


def manuscript(out_pdf: Path, X_train, y_train, results: dict, versions: dict) -> dict:
    """Render the 3-page demo manuscript. Returns accuracy-axes bboxes (pt)."""
    from matplotlib.backends.backend_pdf import PdfPages

    anchors = {}
    with PdfPages(out_pdf) as pdf:
        # — Page 1: title + what-this-is + results table. —
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(
            0.5,
            0.92,
            "MNIST Classification: a worked example",
            ha="center",
            fontsize=18,
            weight="bold",
        )
        fig.text(
            0.5,
            0.88,
            "example-project-mnist · EXAMPLE DATA for SciTeX UI development",
            ha="center",
            fontsize=10,
            style="italic",
        )
        body = (
            f"Models trained on the first {N_TRAIN:,} MNIST training images and "
            f"evaluated on {N_TEST:,} held-out images (fixed seed {SEED}).\n\n"
            f"Logistic regression test accuracy: {results['logreg']:.4f}\n"
            f"kNN (k={KNN_K}, {KNN_TRAIN:,} reference images) test accuracy: "
            f"{results['knn']:.4f}\n\n"
            "Every number in this document was computed by "
            "examples/make_example_project_mnist.py — see provenance.yaml "
            "for dataset, versions, and seeds. "
            "These are example claims, not research findings."
        )
        fig.text(0.1, 0.78, body, va="top", fontsize=11, wrap=True)
        fig.text(
            0.1,
            0.06,
            f"Generated {_utcnow()} · scikit-learn {versions['sklearn']} · "
            f"matplotlib {versions['matplotlib']} · numpy {versions['numpy']}",
            fontsize=8,
            color="gray",
        )
        pdf.savefig(fig)
        plt.close(fig)

        # — Page 2: real MNIST digit samples. —
        fig, axes = plt.subplots(2, 10, figsize=(8.5, 4))
        rng = np.random.RandomState(SEED)
        for ax, i in zip(axes.flat, rng.choice(len(X_train), 20, replace=False)):
            ax.imshow(X_train[i].reshape(28, 28), cmap="gray")
            ax.set_title(str(y_train[i]), fontsize=10)
            ax.axis("off")
        fig.suptitle("MNIST training samples (real data)", fontsize=14)
        fig.tight_layout()
        pdf.savefig(fig)
        digits_png = out_pdf.parent / "figz" / "mnist_digits.png"
        digits_png.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(digits_png, dpi=100)
        plt.close(fig)

        # — Page 3: accuracy figure (anchors point here). —
        fig = plt.figure(figsize=(8.5, 11))
        ax = fig.add_axes([0.15, 0.55, 0.7, 0.3])
        names = ["Logistic\nregression", f"kNN\n(k={KNN_K})"]
        vals = [results["logreg"], results["knn"]]
        floor = min(0.8, min(vals) - 0.05)
        bars = ax.bar(names, vals, bottom=floor, color=["#2da44e", "#0967da"])
        ax.set_ylim(floor, 1.0)
        ax.set_ylabel("Test accuracy")
        ax.set_title("MNIST test accuracy (computed, n=%d)" % N_TEST)
        for b, v in zip(bars, vals):
            ax.text(
                b.get_x() + b.get_width() / 2,
                v + 0.004,
                f"{v:.4f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )
        fig.text(
            0.1,
            0.45,
            "Figure 1. Held-out test accuracy of the two example classifiers. "
            "Values are computed by the generator script; claim anchors in "
            "claims.json point at these bars.",
            fontsize=10,
            wrap=True,
        )
        pdf.savefig(fig)
        # Anchor bbox in PDF points, from the axes position.
        pos = ax.get_position()
        x0, y0 = pos.x0 * PAGE_W_PT, pos.y0 * PAGE_H_PT
        x1, y1 = pos.x1 * PAGE_W_PT, pos.y1 * PAGE_H_PT
        anchors["accuracy_axes_pt"] = [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]
        acc_png = out_pdf.parent / "figz" / "mnist_accuracy.png"
        fig.savefig(acc_png, dpi=100)
        plt.close(fig)
    return anchors


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(OUT_DIR), help="Output bundle dir.")
    parser.add_argument("--quick", action="store_true",
                        help="Smoke mode: 1000 train / 200 test (fast, different numbers).")
    args = parser.parse_args(argv)

    global N_TRAIN, N_TEST, KNN_TRAIN
    if args.quick:
        N_TRAIN, N_TEST, KNN_TRAIN = 1000, 200, 500

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    import sklearn

    versions = {
        "sklearn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
        "numpy": np.__version__,
    }
    stamp = _utcnow()

    X, y = load_mnist()
    X_train, y_train, X_test, y_test = split(X, y)
    logreg = train_logreg(X_train, y_train)
    knn = train_knn(X_train, y_train)
    acc_lr = accuracy(logreg, X_test, y_test)
    acc_knn = accuracy(knn, X_test, y_test)
    results = {"logreg": acc_lr, "knn": acc_knn}

    anchors = manuscript(out / "manuscript.pdf", X_train, y_train, results, versions)
    ax = anchors["accuracy_axes_pt"]
    # Two claim anchors over the accuracy bars (page 3, PDF points).
    mid = (ax[0] + ax[2]) / 2
    anchors_lr = [round(ax[0], 1), round(ax[1], 1), round(mid, 1), round(ax[3], 1)]
    anchors_knn = [round(mid, 1), round(ax[1], 1), round(ax[2], 1), round(ax[3], 1)]

    claims = {
        "schema": "scitex-clew.claims/v1",
        "claims": [
            {
                "claim_id": "mnist_logreg_accuracy",
                "file_path": "manuscript.pdf",
                "line_number": 3,
                "claim_type": "statistic",
                "claim_value": f"logistic regression test accuracy = {acc_lr:.4f}",
                "source_session": "sess_train",
                "source_file": "examples/make_example_project_mnist.py",
                "source_hash": None,
                "registered_at": stamp,
                "verified_at": None,
                "status": "registered",
                "anchor": {"page": 3, "bbox": anchors_lr},
            },
            {
                "claim_id": "mnist_knn_accuracy",
                "file_path": "manuscript.pdf",
                "line_number": 3,
                "claim_type": "statistic",
                "claim_value": f"kNN(k={KNN_K}) test accuracy = {acc_knn:.4f}",
                "source_session": "sess_train",
                "source_file": "examples/make_example_project_mnist.py",
                "source_hash": None,
                "registered_at": stamp,
                "verified_at": None,
                "status": "registered",
                "anchor": {"page": 3, "bbox": anchors_knn},
            },
            {
                "claim_id": "mnist_model_comparison",
                "file_path": "manuscript.pdf",
                "line_number": 1,
                "claim_type": "value",
                "claim_value": (
                    f"logreg minus kNN accuracy = {acc_lr - acc_knn:+.4f} "
                    f"on {N_TEST} held-out images"
                ),
                "source_session": "sess_train",
                "source_file": "examples/make_example_project_mnist.py",
                "source_hash": None,
                "registered_at": stamp,
                "verified_at": None,
                "status": "registered",
            },
        ],
    }
    (out / "claims.json").write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")

    (out / "dag.mmd").write_text(
        "graph LR\n"
        "    S1[Source<br/>OpenML mnist_784 v1] --> I1[Input<br/>70k images]\n"
        "    I1 --> P1[Processing<br/>seeded split]\n"
        "    P1 --> O1[Output<br/>train/test]\n"
        "    O1 --> P2[Processing<br/>logreg + kNN train]\n"
        "    P2 --> O2[Output<br/>test accuracies]\n"
        "    O2 --> C1[Claim<br/>mnist_logreg_accuracy]\n"
        "    O2 --> C2[Claim<br/>mnist_knn_accuracy]\n"
        "    O2 --> C3[Claim<br/>mnist_model_comparison]\n",
        encoding="utf-8",
    )

    manuscript_hash = sha256_file(out / "manuscript.pdf")
    claims_hash = sha256_file(out / "claims.json")
    (out / "provenance.yaml").write_text(
        "schema: scitex-clew.provenance/v1\n"
        "project:\n"
        "  name: example-project-mnist\n"
        "  commit: null  # regenerated, not versioned upstream\n"
        "dataset:\n"
        "  name: mnist_784\n"
        "  source: OpenML\n"
        "  version: 1\n"
        "  split:\n"
        f"    train: {N_TRAIN}\n"
        f"    test: {N_TEST}\n"
        f"    seed: {SEED}\n"
        f"    knn_reference: {KNN_TRAIN}\n"
        "sessions:\n"
        "  sess_train:\n"
        "    role: processing\n"
        "    script: examples/make_example_project_mnist.py\n"
        "    inputs:\n"
        f"      - hash: openml:mnist_784:v1\n"
        "        path: mnist_784 (OpenML)\n"
        "    outputs:\n"
        f"      - hash: {manuscript_hash}\n"
        "        path: manuscript.pdf\n"
        f"      - hash: {claims_hash}\n"
        "        path: claims.json\n"
        "environment:\n"
        f"  scikit-learn: {versions['sklearn']}\n"
        f"  matplotlib: {versions['matplotlib']}\n"
        f"  numpy: {versions['numpy']}\n"
        f"  generated_at: {stamp}\n"
        f"  results: {{logreg: {acc_lr:.6f}, knn: {acc_knn:.6f}}}\n",
        encoding="utf-8",
    )

    (out / "README.md").write_text(
        "# example-project-mnist — seed bundle for the SciTeX example project\n\n"
        "EXAMPLE DATA for SciTeX UI development (writer / live-paper /\n"
        "agentic-journal panes). Not research findings: every number was\n"
        "computed by `examples/make_example_project_mnist.py` — regenerate\n"
        "with:\n\n"
        "```\n"
        "uv pip install scikit-learn matplotlib numpy  # generator-only deps\n"
        "python examples/make_example_project_mnist.py\n"
        "```\n\n"
        "Hub side drops this directory into the `example-project-mnist`\n"
        "user project; `/apps/live-paper/?working_dir=<this dir>` renders it.\n\n"
        "```\n"
        "example-project-mnist/\n"
        "  manuscript.pdf   # 3-page demo paper (real MNIST images + computed figure)\n"
        "  claims.json      # 3 claims carrying the computed accuracies\n"
        "  dag.mmd          # fetch -> split -> train -> evaluate -> render\n"
        "  provenance.yaml  # dataset, script, versions, seeds\n"
        "  figz/            # accuracy + digit-sample PNGs (also in the PDF)\n"
        "```\n",
        encoding="utf-8",
    )

    print(f"logreg test accuracy: {acc_lr:.4f}")
    print(f"knn    test accuracy: {acc_knn:.4f}")
    print(f"bundle: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
