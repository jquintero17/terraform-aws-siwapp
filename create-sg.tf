# create-sg.tf
 
data "http" "myip" {
  url = "http://ipv4.icanhazip.com"
}
 
resource "aws_security_group" "sg" {
  name        = "$terraform-ingress-sg"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.vpc.id
 
  ingress = [{
    description      = "So insecure"
    protocol         = var.sg_ingress_proto
    from_port        = var.sg_ingress_all
    to_port          = var.sg_ingress_all
    cidr_blocks      = [var.sg_all_cidr_block]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
 
  }]
 
  egress = [{
    description      = "All traffic"
    protocol         = var.sg_egress_proto
    from_port        = var.sg_egress_all
    to_port          = var.sg_egress_all
    cidr_blocks      = [var.sg_all_cidr_block]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
 
  }]
 
  tags = {
    "Owner" = var.owner
    "Name"  = "siwapp-sg"
  }
}