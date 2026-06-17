"""
face_detection - Proxy module that imports from face_alignment package.
Wav2Lip expects 'import face_detection' but the package is installed as 'face_alignment'.
"""
from face_alignment import FaceAlignment, LandmarksType, NetworkSize

# Alias for backwards compatibility
__all__ = ["FaceAlignment", "LandmarksType", "NetworkSize"]
