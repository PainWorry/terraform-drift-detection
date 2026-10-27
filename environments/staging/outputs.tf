output "canary_security_group_id" {
  description = "Security Group ID of the drift canary resource"
  value       = aws_security_group.drift_canary.id
}

output "canary_security_group_console_url" {
  description = "One-click AWS Management Console deep link for canary Security Group"
  value       = "https://${var.aws_region}.console.aws.amazon.com/ec2/home?region=${var.aws_region}#SecurityGroup:groupId=${aws_security_group.drift_canary.id}"
}
