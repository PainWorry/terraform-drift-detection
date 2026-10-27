variable "aws_region" {
  type        = string
  description = "AWS deployment region"
  default     = "ap-southeast-1"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the drift canary security group and S3 Gateway Endpoint will be deployed"
  default     = null
}

variable "route_table_ids" {
  type        = list(string)
  description = "List of route table IDs to associate with the S3 Gateway VPC Endpoint"
  default     = []
}
