variable "region" {
  description = "AWS region. Defaults to London — fitting for a UK sovereign-capability demo."
  type        = string
  default     = "eu-west-2"
}

variable "instance_type" {
  description = "GPU instance. g5.xlarge = 1x NVIDIA A10G (24 GB)."
  type        = string
  default     = "g5.xlarge"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair for SSH access."
  type        = string
}

variable "ssh_ingress_cidr" {
  description = "CIDR allowed to SSH (port 22). Set to your IP, e.g. 1.2.3.4/32."
  type        = string
}

variable "domain" {
  description = "Public hostname served by Caddy (point its A record at the Elastic IP)."
  type        = string
  default     = "aletheia.stenoai.co"
}

variable "adapter_bucket_name" {
  description = "S3 bucket to hold the converted PEFT adapter. Must be globally unique."
  type        = string
}

variable "root_volume_gb" {
  description = "Root EBS size. Needs room for ~15 GB base weights + vLLM + CUDA."
  type        = number
  default     = 200
}

variable "repo_url" {
  description = "Git URL the instance clones to get serving code."
  type        = string
  default     = "https://github.com/ruzin/aletheia.git"
}
