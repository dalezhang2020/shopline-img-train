"""Models module for CLIP and Grounding DINO"""

from .clip_encoder import CLIPEncoder
from .grounding_dino import GroundingDINODetector

__all__ = ["CLIPEncoder", "GroundingDINODetector"]
