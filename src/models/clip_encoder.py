"""CLIP model for image feature extraction"""

import logging
from typing import List, Union, Optional
from pathlib import Path
import numpy as np
import torch
import open_clip
from PIL import Image
from tqdm import tqdm

logger = logging.getLogger(__name__)


class CLIPEncoder:
    """CLIP encoder for extracting image and text embeddings"""

    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "openai",
        device: Optional[str] = None,
        batch_size: int = 32,
    ):
        """
        Initialize CLIP encoder

        Args:
            model_name: CLIP model architecture
            pretrained: Pretrained weights source
            device: Device to use (cuda/cpu)
            batch_size: Batch size for encoding
        """
        self.model_name = model_name
        self.pretrained = pretrained
        self.batch_size = batch_size

        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Loading CLIP model: {model_name} ({pretrained})")
        logger.info(f"Using device: {self.device}")

        # Load model and preprocessing
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name=model_name,
            pretrained=pretrained,
            device=self.device,
        )

        self.tokenizer = open_clip.get_tokenizer(model_name)

        # Set model to evaluation mode
        self.model.eval()

        # Get embedding dimension
        self.embedding_dim = self.model.visual.output_dim

        logger.info(f"CLIP model loaded successfully. Embedding dim: {self.embedding_dim}")

    @torch.no_grad()
    def encode_image(self, image: Union[Image.Image, np.ndarray]) -> np.ndarray:
        """
        Encode a single image to embedding vector

        Args:
            image: PIL Image or numpy array

        Returns:
            Normalized embedding vector
        """
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        # Preprocess and move to device
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        # Get embedding
        embedding = self.model.encode_image(image_tensor)

        # Normalize
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.cpu().numpy()[0]

    @torch.no_grad()
    def encode_images_batch(
        self,
        images: List[Union[Image.Image, np.ndarray]],
        show_progress: bool = True,
    ) -> np.ndarray:
        """
        Encode multiple images in batches

        Args:
            images: List of images
            show_progress: Show progress bar

        Returns:
            Array of embeddings (N, embedding_dim)
        """
        embeddings = []

        # Convert numpy arrays to PIL Images
        pil_images = []
        for img in images:
            if isinstance(img, np.ndarray):
                pil_images.append(Image.fromarray(img))
            else:
                pil_images.append(img)

        # Process in batches
        iterator = range(0, len(pil_images), self.batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Encoding images")

        for i in iterator:
            batch = pil_images[i:i + self.batch_size]

            # Preprocess batch
            batch_tensors = torch.stack([
                self.preprocess(img) for img in batch
            ]).to(self.device)

            # Get embeddings
            batch_embeddings = self.model.encode_image(batch_tensors)

            # Normalize
            batch_embeddings = batch_embeddings / batch_embeddings.norm(dim=-1, keepdim=True)

            embeddings.append(batch_embeddings.cpu().numpy())

        # Concatenate all batches
        embeddings = np.vstack(embeddings)

        logger.info(f"Encoded {len(embeddings)} images")
        return embeddings

    @torch.no_grad()
    def encode_image_paths(
        self,
        image_paths: List[Path],
        show_progress: bool = True,
    ) -> np.ndarray:
        """
        Encode images from file paths

        Args:
            image_paths: List of image file paths
            show_progress: Show progress bar

        Returns:
            Array of embeddings
        """
        embeddings = []

        iterator = range(0, len(image_paths), self.batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Encoding images from files")

        for i in iterator:
            batch_paths = image_paths[i:i + self.batch_size]
            batch_images = []

            for path in batch_paths:
                try:
                    img = Image.open(path).convert("RGB")
                    batch_images.append(img)
                except Exception as e:
                    logger.warning(f"Failed to load image {path}: {e}")
                    # Use a blank image as placeholder
                    batch_images.append(Image.new("RGB", (224, 224)))

            # Preprocess batch
            batch_tensors = torch.stack([
                self.preprocess(img) for img in batch_images
            ]).to(self.device)

            # Get embeddings
            batch_embeddings = self.model.encode_image(batch_tensors)

            # Normalize
            batch_embeddings = batch_embeddings / batch_embeddings.norm(dim=-1, keepdim=True)

            embeddings.append(batch_embeddings.cpu().numpy())

        embeddings = np.vstack(embeddings)
        logger.info(f"Encoded {len(embeddings)} images from files")
        return embeddings

    @torch.no_grad()
    def encode_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Encode text to embedding vector(s)

        Args:
            text: Single text string or list of strings

        Returns:
            Normalized embedding vector(s)
        """
        if isinstance(text, str):
            text = [text]

        # Tokenize
        text_tokens = self.tokenizer(text).to(self.device)

        # Get embeddings
        embeddings = self.model.encode_text(text_tokens)

        # Normalize
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

        return embeddings.cpu().numpy()

    def compute_similarity(
        self,
        image_embedding: np.ndarray,
        database_embeddings: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and database embeddings

        Args:
            image_embedding: Query embedding (embedding_dim,)
            database_embeddings: Database embeddings (N, embedding_dim)

        Returns:
            Similarity scores (N,)
        """
        # Ensure normalized
        image_embedding = image_embedding / np.linalg.norm(image_embedding)

        # Compute cosine similarity
        similarities = database_embeddings @ image_embedding

        return similarities
