from pathlib import Path
import logging
import boto3

from common import AWS_REGION, S3_BUCKET

logger = logging.getLogger(__name__)

class ArtifactService:
    def __init__(self):
        self.s3 = boto3.client("s3", region_name=AWS_REGION)

    def download_if_missing(self, s3_key: str, local_path: Path) -> None:
        """Download a file from S3 if it does not exist locally."""

    
        if local_path.exists():
            return

        local_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading %s...", s3_key)

        self.s3.download_file(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Filename=str(local_path),
        )

        logger.info("%s downloaded successfully.", s3_key)