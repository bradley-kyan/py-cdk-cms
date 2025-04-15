#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import App
from py_cdk_cms import (
    vpc_stack as VPCStack,
    ecs_stack as ECSStack,
    rds_stack as RDSStack,
    ecr_manager_stack as ECRManagerStack,
    dynamo_db_stack as DynamoDBStack,
)

import boto3
import json
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class CMSSite(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        env = cdk.Environment(
            account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
            region=os.environ.get("CDK_DEFAULT_REGION"),
        )

        vpc_stack = VPCStack.VPCStack(self, "VPCStack", env=env)
        vpc = vpc_stack.vpc

        ecr_stack = ECRManagerStack.ECRManagerStack(self, "ECRStack", env=env)
        ecr_repo = ecr_stack.ecr_repo

        rds_stack = RDSStack.RDSStack(self, "RDSStack", vpc=vpc, env=env)

        # Create ECS stack with the container environments
        ecs_stack = ECSStack.ECSStack(
            self,
            "ECSStack",
            vpc=vpc,
            ecr_repository=ecr_repo,
            env=env,
        )

        # ddb_stack = DynamoDBStack.DynamoDBStack(self, "DynamoDBStack")

        ecr_stack.add_dependency(vpc_stack)
        rds_stack.add_dependency(vpc_stack)
        ecs_stack.add_dependency(rds_stack)
        ecs_stack.add_dependency(ecr_stack)
        # ddb_stack.add_dependency(ecs_stack)


app = CMSSite()

app.synth()
