variable "github_repo" {
  description = "GitHub repository in format: owner/repo-name"
  type        = string
  default     = "your-username/your-repo"
}

variable "branch_name" {
  description = "Branch to monitor"
  type        = string
  default     = "main"
}

variable "notification_email" {
  description = "Email address for compliance alerts"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
