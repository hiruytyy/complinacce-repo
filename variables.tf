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

variable "bedrock_model_id" {
  description = "Bedrock model ID for AI analysis"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}

variable "bedrock_max_tokens" {
  description = "Maximum tokens for Bedrock response"
  type        = number
  default     = 1500
}

variable "bedrock_temperature" {
  description = "Temperature for Bedrock model (0.0-1.0)"
  type        = number
  default     = 0.3
}
