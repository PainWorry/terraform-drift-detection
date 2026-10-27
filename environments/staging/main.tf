terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    key          = "staging/drift-canary/terraform.tfstate"
    region       = "ap-southeast-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region      = var.aws_region
  max_retries = 25

  default_tags {
    tags = {
      Environment = "staging"
      ManagedBy   = "Terraform"
      Project     = "CloudInfrastructure"
    }
  }
}

# Drift Canary Security Group
resource "aws_security_group" "drift_canary" {
  name        = "onelink-staging-drift-canary-sg"
  description = "Security group for live drift detection canary testing"
  vpc_id      = var.vpc_id

  ingress {
    description = "Managed by Terraform - Baseline HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  tags = {
    Environment = "staging"
    ManagedBy   = "Terraform"
    Purpose     = "DriftCanary"
  }

  lifecycle {
    ignore_changes = [
      tags["aws:backup:job-id"]
    ]
  }
}

# Free S3 Gateway VPC Endpoint (Eliminates NAT Gateway Egress Costs for State/Artifacts)
resource "aws_vpc_endpoint" "s3" {
  count             = var.vpc_id != null ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.route_table_ids

  tags = {
    Name        = "onelink-staging-s3-gateway-endpoint"
    Environment = "staging"
    ManagedBy   = "Terraform"
  }
}
