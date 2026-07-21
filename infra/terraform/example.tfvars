# Copy to terraform.tfvars and fill in. terraform.tfvars is git-ignored.
adapter_bucket_name = "aletheia-adapter-ruzin" # globally-unique S3 bucket name (required)

# SSH is optional — the instance is reachable via SSM Session Manager without a key.
# Set both of these only if you want SSH access:
# key_name         = "my-ec2-keypair"    # an existing EC2 key pair name
# ssh_ingress_cidr = "203.0.113.4/32"    # your public IP /32

# Optional overrides:
# region        = "eu-west-2"            # London (default)
# domain        = "aletheia.stenoai.co"
# instance_type = "g6.xlarge"            # L4 24GB (default); g4dn.xlarge for T4 16GB
# use_spot      = true                   # false for on-demand
# spot_max_price = ""                    # empty = cap at on-demand price
