"""Models module for CLIP and Grounding DINO"""

from .clip_encoder import CLIPEncoder

# GroundingDINO is optional - only import if cv2 is available
try:
    from .grounding_dino import GroundingDINODetector
    __all__ = ["CLIPEncoder", "GroundingDINODetector"]
except ImportError:
    # cv2 not installed - GroundingDINO not available (production mode)
    __all__ = ["CLIPEncoder"]
