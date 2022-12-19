# create-instance.tf
resource "aws_instance" "dblb" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_db_lb"
    "KeepInstanceRunning" = "false"
    "ansible_group"       = "db_lb"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
  }
}

resource "aws_instance" "db1" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_db1"
    "KeepInstanceRunning" = "false"
    "ansible_group"       = "db"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
    "Lead"                = "true"
  }
}

resource "aws_instance" "db2" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_db2"
    "KeepInstanceRunning" = "false"
    "ansible_group"       = "db"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
    "Lead"                = "false"
  }
}

resource "aws_instance" "db3" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_db3"
    "KeepInstanceRunning" = "false"
    "ansible_group"       = "db"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
    "Lead"                = "false"
  }
}

resource "aws_instance" "applb" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_app_lb"
    "KeepInstanceRunning" = "false"
    "ansible_group"	      = "app_lb"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
  }
}

resource "aws_instance" "app1" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_app1"
    "KeepInstanceRunning" = "false"
    "ansible_group"	      = "app"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
  }
}

resource "aws_instance" "app2" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_app2"
    "KeepInstanceRunning" = "false"
    "ansible_group"       = "app"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
  }
}

resource "aws_instance" "app3" {
  ami                         = var.instance_ami
  availability_zone           = "${var.aws_region}${var.aws_region_az}"
  instance_type               = var.instance_type
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  subnet_id                   = aws_subnet.subnet.id
  key_name                    = var.key_pair
 
  root_block_device {
    delete_on_termination = true
    encrypted             = false
    volume_size           = var.root_device_size
    volume_type           = var.root_device_type
  }
 
  tags = {
    "Owner"               = var.owner
    "Name"                = "siwapp_app3"
    "KeepInstanceRunning" = "false"
    "ansible_group"       = "app"
    "ApplicationName"     = "siwapp"
    "Scope"               = "prod"
  }
  provisioner "remote-exec" {
    inline =  ["echo Done!"]

    connection {
      host        = self.public_ip
      type        = "ssh"
      user        = "centos"
      private_key = file(var.pvt_key)
    }
  }
  provisioner "local-exec" {
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u centos -i ansible/vars/aws_ec2.yml --private-key ${var.pvt_key} ansible/site.yml"
  }
}