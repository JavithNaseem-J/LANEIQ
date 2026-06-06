# LANEIQ — Deployment and Cloud Infrastructure Guide

This document contains the IAM policy configurations, security group settings, and EC2 bootstrap scripts required to deploy the LANEIQ stack to AWS.

---

## 1. IAM Role Config (`FreightMindEC2Role`)

Attach this role to your EC2 instance. It grants access to ECR for pulling Docker images, read-write access to S3 for monitoring data/Evidently reports, and CloudWatch permissions for logging.

### Trust Relationship
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### IAM Policy Permissions
Create a policy named `LaneIQ_EC2_Permissions` and attach it to the role:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRReadAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::freightmind-bucket",
        "arn:aws:s3:::freightmind-bucket/*"
      ]
    },
    {
      "Sid": "CloudWatchMetricsAndLogs",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 2. Security Group Settings

Create a security group `laneiq-sg` with the following inbound rules:

| Protocol | Port Range | Source | Description |
|---|---|---|---|
| TCP | 22 | `My IP` | SSH Access |
| TCP | 8000 | `0.0.0.0/0` | FastAPI Web API |
| TCP | 8501 | `0.0.0.0/0` | Streamlit Dashboard |

---

## 3. EC2 Bootstrap Script (`bootstrap.sh`)

Run the following commands on a fresh Amazon Linux 2023 `t3.medium` instance to install Docker, Docker Compose, Git, and configure the application directory structure.

```bash
#!/bin/bash
set -e

# Update packages
sudo dnf update -y

# Install Docker
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# Install Docker Compose (v2)
sudo dnf install -y docker-compose-plugin

# Verify installations
docker --version
docker compose version

# Create application directory
sudo mkdir -p /home/ec2-user/laneiq
sudo chown -R ec2-user:ec2-user /home/ec2-user/laneiq

echo "Bootstrap completed successfully! Log out and back in to apply group changes."
```

---

## 4. Setting up the App on EC2

After SSH-ing into the instance:

1. Copy the `docker-compose.yml` to `/home/ec2-user/laneiq/docker-compose.yml`.
2. Create `/home/ec2-user/laneiq/.env` with your API keys:
   ```env
   GROQ_API_KEY=gsk_your_key_here
   MARINETRAFFIC_KEY=your_marinetraffic_key
   REDIS_URL=redis://redis:6379/0
   AWS_REGION=us-east-1
   ```
3. Authenticate Docker with Amazon ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.us-east-1.amazonaws.com
   ```
4. Start the stack:
   ```bash
   cd /home/ec2-user/laneiq
   docker compose up -d
   ```
