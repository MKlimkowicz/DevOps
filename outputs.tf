output "grafana_url" {
  value       = "http://${aws_lb.public.dns_name}/grafana/"
  description = "Grafana UI (HTTP)"
}

output "prometheus_url" {
  value       = "http://${aws_lb.public.dns_name}"
  description = "Prometheus UI (HTTP)"
}
