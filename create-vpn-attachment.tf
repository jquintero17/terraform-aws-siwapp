resource "aws_vpn_gateway" "vpn" {
  tags = {
    Name = "Oxy Demo GW"
  }
}

resource "aws_vpn_gateway_attachment" "vpn_attachment" {
  vpc_id         = aws_vpc.vpc.id
  vpn_gateway_id = aws_vpn_gateway.vpn.id
}

resource "aws_vpn_gateway_route_propagation" "oxyroute" {
  vpn_gateway_id = aws_vpn_gateway.vpn.id
  route_table_id = aws_route_table.rt.id
}