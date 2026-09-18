"""Lazily-created, container-cached boto3 clients.

Two reasons this is not just ``boto3.client(...)`` at the top of each handler:

* Creating a client parses botocore's service JSON and costs real milliseconds.
  A Lambda container serves many invocations, so it should happen once.
* Importing boto3 at module scope would make every pure-logic test need the AWS
  SDK. The imports here are inside the functions on purpose.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .config import load_config

__all__ = ["dynamodb_resource", "reset_clients", "s3_client", "sqs_client"]


@lru_cache(maxsize=1)
def s3_client() -> Any:
    import boto3
    from botocore.config import Config as BotoConfig

    return boto3.client(
        "s3",
        region_name=load_config().region,
        # SigV4 is required for presigned URLs to be accepted by newer buckets.
        config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 3}),
    )


@lru_cache(maxsize=1)
def sqs_client() -> Any:
    import boto3

    return boto3.client("sqs", region_name=load_config().region)


@lru_cache(maxsize=1)
def dynamodb_resource() -> Any:
    import boto3

    return boto3.resource("dynamodb", region_name=load_config().region)


def reset_clients() -> None:
    """Drop cached clients. Tests only."""
    s3_client.cache_clear()
    sqs_client.cache_clear()
    dynamodb_resource.cache_clear()
