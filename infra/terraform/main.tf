terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# AWS Deep Learning Base AMI: NVIDIA drivers + CUDA preinstalled, no frameworks
# (we pip install vLLM ourselves). Ubuntu 22.04.
data "aws_ami" "dlami" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# --- S3 bucket for the converted PEFT adapter -----------------------------------------
resource "aws_s3_bucket" "adapter" {
  bucket = var.adapter_bucket_name
}

resource "aws_s3_bucket_public_access_block" "adapter" {
  bucket                  = aws_s3_bucket.adapter.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- IAM: instance can read the adapter bucket ----------------------------------------
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "instance" {
  name               = "aletheia-instance"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "s3_read" {
  statement {
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.adapter.arn, "${aws_s3_bucket.adapter.arn}/*"]
  }
}

resource "aws_iam_role_policy" "s3_read" {
  name   = "aletheia-s3-read"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.s3_read.json
}

# Let AWS Systems Manager manage the box (handy for start/stop + shell without SSH keys).
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "instance" {
  name = "aletheia-instance"
  role = aws_iam_role.instance.name
}

# --- Networking (default VPC) ---------------------------------------------------------
data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "web" {
  name        = "aletheia-web"
  description = "Aletheia: HTTP/HTTPS public, SSH restricted"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP (Caddy / ACME challenge)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "SSH (restricted)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- The GPU instance -----------------------------------------------------------------
resource "aws_instance" "aletheia" {
  ami                    = data.aws_ami.dlami.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  iam_instance_profile   = aws_iam_instance_profile.instance.name
  vpc_security_group_ids = [aws_security_group.web.id]

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    adapter_s3 = "s3://${aws_s3_bucket.adapter.bucket}/adapter"
    repo_url   = var.repo_url
  })

  # Spot request (cheaper). "persistent" + "stop" means an interruption stops the
  # instance (EIP + EBS survive) and it restarts when capacity returns, instead of
  # being terminated. start.sh / stop.sh still work for manual cost control.
  dynamic "instance_market_options" {
    for_each = var.use_spot ? [1] : []
    content {
      market_type = "spot"
      spot_options {
        spot_instance_type             = "persistent"
        instance_interruption_behavior = "stop"
        max_price                      = var.spot_max_price != "" ? var.spot_max_price : null
      }
    }
  }

  tags = { Name = "aletheia" }
}

resource "aws_eip" "aletheia" {
  instance = aws_instance.aletheia.id
  domain   = "vpc"
  tags     = { Name = "aletheia" }
}
