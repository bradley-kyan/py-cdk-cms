from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets
)
import aws_cdk as cdk
import logging
import os
from datetime import datetime
from constructs import Construct

logger = logging.getLogger(__name__)

class ECRManagerStack(Stack):
    docker_image: ecr_assets.DockerImageAsset
    ecr_repo: ecr.Repository

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.ecr_repo = self.create_ecr_repo("cms-ecr-repo")

    def create_ecr_repo(self, repo_name: str) -> ecr.Repository:
        
        enviornment = os.environ.get("ENVIRONMENT")
        
        if enviornment is None:
            logger.error("ENVIRONMENT not set")
            raise Exception("ENVIRONMENT not set")
        elif enviornment == "dev":
            logger.info("Creating ECR repo in dev environment")
            remove_policy = cdk.RemovalPolicy.DESTROY
        elif enviornment == "prod":
            logger.info("Creating ECR repo in prod environment")
            remove_policy = cdk.RemovalPolicy.RETAIN
        
        repo = ecr.Repository(
            self,
            repo_name,
            repository_name=repo_name,
            removal_policy=remove_policy,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
            image_scan_on_push=True,
            encryption=ecr.RepositoryEncryption.AES_256,
        )
        
        return repo
    
    def add_docker_image_to_ecr(self, directory_path: str, build_args: dict) -> ecr_assets.DockerImageAsset:
        self.docker_image = ecr_assets.DockerImageAsset(
            self,
            "cms_docker_image",
            directory=directory_path,
            build_args=build_args          
        )
        return self.docker_image

        

    