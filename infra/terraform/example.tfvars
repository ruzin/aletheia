# Copy to terraform.tfvars and fill in. terraform.tfvars is git-ignored.
key_name            = "my-ec2-keypair"          # an existing EC2 key pair name
ssh_ingress_cidr    = "203.0.113.4/32"          # your public IP /32
adapter_bucket_name = "aletheia-adapter-ruzin"  # globally-unique S3 bucket name

# Optional overrides:
# region   = "eu-west-2"                 # London (default)
# domain   = "aletheia.stenoai.co"
# instance_type = "g5.xlarge"
