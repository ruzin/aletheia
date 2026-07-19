output "public_ip" {
  description = "Elastic IP — point the domain's A record here."
  value       = aws_eip.aletheia.public_ip
}

output "instance_id" {
  description = "EC2 instance id (for start/stop scripts)."
  value       = aws_instance.aletheia.id
}

output "adapter_bucket" {
  description = "S3 bucket for the converted PEFT adapter."
  value       = aws_s3_bucket.adapter.bucket
}

output "adapter_s3_uri" {
  description = "Upload the converted adapter here (scripts/upload_adapter_s3.sh)."
  value       = "s3://${aws_s3_bucket.adapter.bucket}/adapter"
}

output "domain" {
  value = var.domain
}

output "region" {
  value = var.region
}

output "next_steps" {
  value = <<-EOT
    1. Point ${var.domain} A record -> ${aws_eip.aletheia.public_ip}
    2. Upload the adapter:  scripts/upload_adapter_s3.sh ${aws_s3_bucket.adapter.bucket}
    3. Watch it come up:    ssh ubuntu@${aws_eip.aletheia.public_ip} 'tail -f /var/log/aletheia-bootstrap.log'
    4. Smoke test:          scripts/smoke_test.sh https://${var.domain}
  EOT
}
