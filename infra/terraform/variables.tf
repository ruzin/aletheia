variable "region" {
  description = "AWS region. Defaults to London — fitting for a UK sovereign-capability demo."
  type        = string
  default     = "eu-west-2"
}

variable "instance_type" {
  description = "GPU instance. g6.xlarge = 1x NVIDIA L4 (24 GB) — cheaper than g5's A10G, same 24 GB so the base+adapter stack fits unchanged."
  type        = string
  default     = "g6.xlarge"
}

variable "use_spot" {
  description = "Run the instance as a Spot request (~50-70% cheaper, can be interrupted). Requires the 'All G and VT Spot Instance Requests' quota."
  type        = bool
  default     = true
}

variable "spot_max_price" {
  description = "Max hourly Spot price (USD). Empty string = cap at the on-demand price."
  type        = string
  default     = ""
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
