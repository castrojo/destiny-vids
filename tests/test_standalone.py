"""The standalone-video batch suite lives on the branch that builds it
(`fix/bluefin-video-batch-ci`); this file carries the one pin that branch's
training-CTA commit needs on THIS branch: the approved LF training card's
bytes. When the branches meet, the two files merge — same name on purpose,
so docs/skills/training-cta/SKILL.md's citation resolves on both.
"""

import hashlib
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_training_cta_is_the_approved_1080p_asset():
    path = REPO_ROOT / "assets/cta/linux-foundation-training-forest.png"
    assert Image.open(path).size == (1920, 1080)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "46d05d65973f64c4811a02f64673db547cb2d403c58caa9fdbddc7b0da5883c5"
    )
