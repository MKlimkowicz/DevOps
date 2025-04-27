resource "aws_instance" "psql" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  tags = {
    Name = "psql"
  }
  user_data = file("${path.module}/scripts/psql_user_data.sh")
  vpc_security_group_ids = [aws_security_group.psql_sg.id]
  subnet_id = element(aws_subnet.private.*.id, 0)
  iam_instance_profile = aws_iam_instance_profile.ec2_ssm_profile.name
}

resource "aws_instance" "monitoring" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  tags = {
    Name = "monitoring"
  }
  user_data = templatefile("${path.module}/scripts/monitoring_user_data.sh", {
    psql_private_ip = aws_instance.psql.private_ip
  })
  vpc_security_group_ids = [aws_security_group.monitoring_sg.id]
  subnet_id = element(aws_subnet.private.*.id, 1)
  iam_instance_profile = aws_iam_instance_profile.ec2_ssm_profile.name
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
} 