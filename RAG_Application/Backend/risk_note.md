Owner: [Server 1] Core App & CRM Team | [Server 2] Enterprise Escalation & Compliance Team
Reach: [Server 1] Internal CRM DB & Vector Store (9 tools) | [Server 2] Escalation Events & Audit Trail DB (2 tools)
Logs: [Server 1] In-memory execution logs & RAG metrics | [Server 2] JSON-RPC 2.0 wire protocol logs & HTTP/SSE access logs
Blast Radius: [Server 1] High (internal process crashes if unhandled) | [Server 2] Isolated (microservice crash fails gracefully with network timeout)
Ship Condition: [Server 1] Local unit tests & DB migrations | [Server 2] TLS/HTTPS encryption, Bearer token rotation, VPC egress filtering
