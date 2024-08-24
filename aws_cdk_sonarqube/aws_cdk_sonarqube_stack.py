from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct
from cdk_ec2_key_pair import KeyPair
import os
import base64

class SonarqubeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lookup the existing VPC from VPC stack
        vpc = ec2.Vpc.from_lookup(self, "vpc", vpc_name=os.environ.get("VPC_NAME"))

        # Create a Security Group for SonarQube
        security_group = ec2.SecurityGroup(self, "sonarqubesg",
            vpc=vpc,
            security_group_name="sonarqube-sg",
            description="Allow ssh and http access to EC2 instance",
            allow_all_outbound=True
        )

        # Allow inbound traffic on SSH Port 22 and SonarQube Port 9000
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "Allow SSH access from anywhere")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(9000), "Allow SonarQube access from anywhere")

        # Create an IAM role for the EC2 instance
        role = iam.Role(self, "sonarqubeinstancerole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ReadOnlyAccess")
            ]
        )

        # Create a new key pair and store it into Secrets Manager
        key = KeyPair(self, "mykeypair",
            key_pair_name="aws-sonarqube-keypair", 
            store_public_key=True
        )
        key.grant_read_on_public_key(role)

        # Define the EC2 instance
        instance = ec2.Instance(self, "sonarqubeinstance",
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.medium"),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=security_group,
            role=role,
            key_name=key.key_pair_name,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=30,
                        encrypted=True,
                        delete_on_termination=False,
                        volume_type=ec2.EbsDeviceVolumeType.GP3
                    )
                )
            ]
        )

        # Create an Elastic IP (Optional)
        eip = ec2.CfnEIP(self, "eip")

        # Output the Elastic IP address
        CfnOutput(self, "ElasticIPAddress", value=eip.ref, description="Elastic IP Address of SonarQube Server")

        # Associate the Elastic IP with the EC2 instance
        ec2.CfnEIPAssociation(self, "eipassociation",
            eip=eip.ref,
            instance_id=instance.instance_id
        )

        # Path to the docker-compose file (assuming it's in the same directory)
        docker_compose_path = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
        print(docker_compose_path)  # Print the path for debugging

        # Read the docker-compose file content 
        with open(docker_compose_path, "r") as file:
            docker_compose_content = file.read()

        # Encode the content to bytes and then decode using base64
        docker_compose_base64 = base64.b64encode(docker_compose_content.encode("utf-8")).decode("utf-8")

        # Add User Data to install Docker, Docker Compose, and run Docker Compose
        instance.add_user_data(
            f"""#!/bin/bash
            dnf update -y
            dnf install -y docker
            systemctl start docker
            systemctl enable docker
            usermod -aG docker ec2-user

            # Install Docker Compose
            curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose

            echo "vm.max_map_count=262144" >> /etc/sysctl.conf
            echo "fs.file-max=65536" >> /etc/sysctl.conf
            sudo sysctl -p
            sudo usermod -aG docker $USER

            # Decode the Base64 encoded docker-compose.yml content and write it to a file
            echo "{docker_compose_base64}" | base64 --decode > /home/ec2-user/docker-compose.yml
            chown ec2-user:ec2-user /home/ec2-user/docker-compose.yml

            # Run Docker Compose
            cd /home/ec2-user
            docker-compose up -d
            """
        )