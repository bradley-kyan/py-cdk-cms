from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
)
from constructs import Construct
import aws_cdk as cdk
import os
import logging
import boto3
import json

logger = logging.getLogger(__name__)


class ECSStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        ecr_repository: ecr.Repository,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create ECS Cluster
        cluster = ecs.Cluster(self, "CMSCluster", vpc=vpc)

        cluster.enable_fargate_capacity_providers()

        # Security Group for the Fargate
        fargate_service_sg = ec2.SecurityGroup(
            self,
            "FargateServiceSG",
            vpc=vpc,
            description="Security group for Fargate service",
            allow_all_outbound=True,
        )

        # Create Security Group for ALB
        alb_security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True,
        )

        # Allow inbound HTTP traffic to ALB
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from internet",
        )
        # # Allow inbound HTTPS traffic to ALB
        # alb_security_group.add_ingress_rule(
        #     peer=ec2.Peer.any_ipv4(),
        #     connection=ec2.Port.tcp(443),
        #     description="Allow HTTPS traffic from internet",
        # )

        # Allow ALB to communicate with Fargate service
        fargate_service_sg.add_ingress_rule(
            peer=alb_security_group,
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic from ALB",
        )

        # # Add HTTPS traffic if needed
        # fargate_service_sg.add_ingress_rule(
        #     peer=alb_security_group,
        #     connection=ec2.Port.tcp(443),
        #     description="Allow HTTPS traffic from internet",
        # )

        # Allow fargate service to communicate with RDS
        fargate_service_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(3306),
            description="Allow MySQL traffic from Fargate service",
        )

        # Try get the image from ECR
        image_url = os.environ.get("PUBLIC_IMAGE_URL")
        logger.info(f"Image URL: {image_url}")
        print(f"Image URL: {image_url}")

        if image_url is not None:
            logger.info("Image not found in ECR. Creating a new container")
            print("Image not found in ECR. Creating a new container")
            container_image = ecs.ContainerImage.from_registry(image_url)
        elif self.container_image_exists(ecr_repository):
            logger.info("Image found in ECR. Creating a new contianer")
            print("Image found in ECR. Creating a new container")
            container_image = ecs.ContainerImage.from_ecr_repository(
                ecr_repository, "latest"
            )
        else:
            logger.error("Image not found in ECR. Please build and push the image.")
            raise Exception("Image not found in ECR. Please build and push the image.")

        # Create Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "CMSTaskDef",
            memory_limit_mib=1024,
            cpu=256,
        )

        # Grant ecs permissions to pull images from ECR
        ecr_repository.grant_pull(task_definition.task_role)

        # Get the secret value
        secret = self.get_secret_value()

        # Create container environment variables
        if secret:
            container_envs = {
                "WORDPRESS_DB_HOST": secret["host"],
                "WORDPRESS_DB_USER": secret["username"],
                "WORDPRESS_DB_PASSWORD": secret["password"],
                "WORDPRESS_DB_NAME": secret["dbname"],
            }
        else:
            logger.error("Failed to get database credentials")
            return

        # Add container to task def
        container = task_definition.add_container(
            "CMSContainer",
            image=container_image,
            container_name="cms_container",
            environment={
                key: value for key, value in container_envs.items() if value is not None
            },
        )

        # Add port mapping
        container.add_port_mappings(
            ecs.PortMapping(container_port=80),
            ecs.PortMapping(container_port=3306),
        )

        # Create ALB
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "ServiceALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group,
        )

        # Create Fargate Service
        fargate_service = ecs.FargateService(
            self,
            "CMSService",
            cluster=cluster,
            task_definition=task_definition,
            security_groups=[fargate_service_sg],
            desired_count=1,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            min_healthy_percent=95,
            assign_public_ip=False,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT", weight=1
                ),
            ],
        )

        # Allow our fargate service to scale
        scalable_target = fargate_service.auto_scale_task_count(
            min_capacity=0,
            max_capacity=2,
        )
        
        scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=95,
            scale_in_cooldown=cdk.Duration.seconds(60),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )
        scalable_target.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=95,
            scale_in_cooldown=cdk.Duration.seconds(60),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )

        # Create ALB Target Group
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "ServiceTargetGroup",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            # Health check needs to be implemented with the cms
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_http_codes="200-302",
                interval=cdk.Duration.seconds(60),
                timeout=cdk.Duration.seconds(5),
            ),
        )

        # Add listener to ALB
        alb.add_listener("Listener-HTTP", port=80, default_target_groups=[target_group])

        # Associate Fargate Service with Target Group
        fargate_service.attach_to_application_target_group(target_group)

        # Add CloudFormation outputs
        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=alb.load_balancer_dns_name,
            description="Load balancer DNS name",
        )

        CfnOutput(
            self,
            "ServiceSecurityGroupId",
            value=fargate_service_sg.security_group_id,
            description="Security group ID for the Fargate service",
        )

        CfnOutput(
            self,
            "AlbSecurityGroupId",
            value=alb_security_group.security_group_id,
            description="Security group ID for the ALB",
        )

        logger.info("ECS Stack deployed successfully")

    def container_image_exists(self, ecr_repository: ecr.Repository) -> bool:
        """
        Check if the container image exists in ECR.
        """
        try:
            client = boto3.client("ecr")
            response = client.describe_images(
                repositoryName=ecr_repository.repository_name,
                imageIds=[{"imageTag": "latest"}],
            )
            return len(response["imageDetails"]) > 0
        except Exception as e:
            logger.error(f"Error checking image in ECR: {e}")
            return False

    def get_secret_value(self):
        """Get secret value using the secret ARN from RDS stack"""
        secrets_manager_client = boto3.client("secretsmanager")
        try:
            response = secrets_manager_client.get_secret_value(SecretId="cms")
            if "SecretString" in response:
                return json.loads(response["SecretString"])
            logger.error("No SecretString found in response")
            return None
        except Exception as e:
            logger.error(f"Error fetching secret: {e}")
