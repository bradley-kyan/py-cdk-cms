from aws_cdk import (
    Stack,
    aws_rds as rds,
    aws_ec2 as ec2,
)

import aws_cdk as cdk
from constructs import Construct
import logging

logger = logging.getLogger(__name__)


class RDSStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = vpc

        # Create a security group for the RDS instance
        rds_security_group = ec2.SecurityGroup(
            self, "CMSSecurityGroup", vpc=vpc, allow_all_outbound=False
        )

        # Allow inbound traffic on port 3306 from within the VPC
        rds_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.MYSQL_AURORA,
            description="Allow MySQL access from within VPC",
        )

        rds_security_group.add_egress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.MYSQL_AURORA,
            description="Allow MySQL to only access the VPC",
        )

        # Create the Aurora RDS instance
        self.rds_instance = rds.DatabaseCluster(
            self,
            "CMSDatabase",
            engine=rds.DatabaseClusterEngine.aurora_mysql(
                version=rds.AuroraMysqlEngineVersion.VER_3_08_1,
            ),
            default_database_name="cms",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            credentials=rds.Credentials.from_generated_secret("cms", secret_name="cms"),
            security_groups=[rds_security_group],
            port=3306,
            vpc=vpc,
            vpc_subnets={
                "subnet_type": ec2.SubnetType.PRIVATE_WITH_EGRESS,
            },
            storage_encrypted=True,
            cluster_identifier="cms-cluster",
            deletion_protection=True,
            serverless_v2_min_capacity=0,
            serverless_v2_max_capacity=1,
            writer=rds.ClusterInstance.serverless_v2(
                "writer", instance_identifier="writer"
            ),
            readers=[
                rds.ClusterInstance.serverless_v2(
                    "reader", scale_with_writer=True, instance_identifier="reader"
                ),
            ],
            cloudwatch_logs_exports=[
                # "audit",
                "error",
                # "slowquery",
            ],  # DONT INCLUDE GENERAL... DONT MAKE THAT MISTAKE AGAIN!
        )

        cdk.CfnOutput(
            self,
            "RDSEndpoint",
            value=self.rds_instance.cluster_endpoint.hostname,
            description="RDS instance endpoint",
            export_name="RDSEndpoint",
        )
