resource "aws_vpn_gateway_attachment" "vpn_attachment" {
  vpc_id         = aws_vpc.vpc.id
  vpn_gateway_id = "vgw-0774fee884724891a"
}

resource "aws_vpn_gateway_route_propagation" "oxyroute" {
  vpn_gateway_id = "vgw-0774fee884724891a"
  route_table_id = aws_route_table.rt.id
}