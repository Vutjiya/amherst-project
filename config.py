"""
Configuration for Street View dataset creation tool.
"""

from pathlib import Path
from typing import Optional


class Config:
    """Configuration class for dataset creation."""
    
    def __init__(self, 
                 download_dir: str,
                 cutout_dir: str,
                 dataset_name: str = 'dataset.pkl',
                 web_url: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            download_dir: Directory containing download.txt and mapping.txt
            cutout_dir: Directory where cutouts will be saved
            dataset_name: Name of output metadata file
            web_url: Optional web URL for cutouts (for HTML displays)
        """
        self.download_dir = Path(download_dir)
        self.cutout_dir = Path(cutout_dir)
        self.dataset_name = dataset_name
        self.web_url = web_url
        
        # Ensure directories exist
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.cutout_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def download_txt(self):
        """Path to download.txt file."""
        return self.download_dir / 'download.txt'
    
    @property
    def mapping_txt(self):
        """Path to mapping.txt file."""
        return self.download_dir / 'mapping.txt'
    
    @property
    def dataset_path(self):
        """Path to output dataset file."""
        return self.download_dir / self.dataset_name
    
    def validate(self):
        """Validate that required files exist."""
        if not self.download_txt.exists():
            raise FileNotFoundError(f"download.txt not found: {self.download_txt}")
        if not self.mapping_txt.exists():
            raise FileNotFoundError(f"mapping.txt not found: {self.mapping_txt}")

