resource "aws_s3_bucket" "example" {
  bucket = "my-test-bucket-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}
