# Recoverable Error Handling: Server 1 vs Server 2 (Before vs After)

This document contrasts the recoverable error handling behavior between **MCP Server 1** (CRM & Local Tools) and **MCP Server 2** (Ticket Escalation Audit Trail) when queried with an invalid ticket (`TCK-9999`).

---

## 1. Architectural Summary: Server 1 vs Server 2 Error Semantics

| Characteristic | MCP Server 1 (`crm-agent-server-v1`) | MCP Server 2 (`ticket-history-v2`) |
| :--- | :--- | :--- |
| **Transport** | In-Process / Local Registry | HTTP / SSE via FastMCP JSON-RPC 2.0 |
| **Target Tool** | `ticket_lookup(ticket_id)` | `get_ticket(ticket_id)` |
| **Failure Mode** | Local DB lookup returns empty record | Remote JSON-RPC tool returns error payload |
| **Recovery Strategy** | Return `{ "found": false, "error": "NOT_FOUND" }` | Return structured JSON-RPC payload with schema guidance |
| **Agent Impact** | Agent checks local fallback / prompts customer | Agent informs customer of format (`TCK-nnnn`) & stops looping |

---

## 2. MCP Server 1: `ticket_lookup` (Before vs After)

### Before: Unhandled Exception / Missing Key
```json
{
  "status": 500,
  "detail": "KeyError: 'TCK-9999' not in customer_tickets database"
}
```
* **Agent Reaction**: The ReAct agent crashes or produces an unhandled tool exception, abruptly ending the reasoning loop.

### After: Structured Recoverable Response
```json
{
  "found": false,
  "error": "TICKET_NOT_FOUND",
  "ticket_id": "TCK-9999",
  "message": "Ticket TCK-9999 was not found in the local CRM database.",
  "suggestion": "Verify ticket ID format (e.g., TCK-1001 to TCK-1004) or search by customer email."
}
```
* **Agent Trajectory**: The ReAct agent reads the structured payload, notes that the ticket does not exist in local CRM, and queries customer data or politely asks the user to check their ticket ID.

---

## 3. MCP Server 2: `get_ticket` (Before vs After)

### Before: Generic Unrecoverable Error
```json
{
  "error": "Error 3",
  "status": 500
}
```
* **Agent Reaction**: The model receives an opaque code `Error 3`. Having no insight into why it failed, it enters a redundant retry loop with the same parameters or hallucinates an apology.

### After: Structured FastMCP Error with Docstring Guidance
```python
@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """
    Retrieve current status, priority, and resolution for a support ticket.
    Args:
        ticket_id: Format TCK-NNNN (e.g. TCK-1004). Do NOT pass raw numbers.
    Errors (recoverable):
        If not found, returns {"found": False, "error": "TICKET_NOT_FOUND", ...}.
        The model should inform the customer and ask them to verify the ticket number.
    """
```
```json
{
  "found": false,
  "error": "TICKET_NOT_FOUND",
  "ticket_id": "TCK-9999",
  "message": "Ticket TCK-9999 was not found in the escalation audit database. IDs should look like TCK-nnnn (e.g. TCK-1004). Please ask the customer to verify their ticket number."
}
```
* **Agent Trajectory**:
  1. **Thought**: The tool returned `found: false` with specific guidance that ticket IDs follow `TCK-nnnn` and `TCK-9999` is absent from escalation records.
  2. **Action**: Model terminates tool search gracefully without looping.
  3. **Customer Response**:
     > *"I checked our escalation history records, but ticket **TCK-9999** could not be found. Ticket numbers follow the format `TCK-nnnn` (such as `TCK-1004`). Could you please double-check your ticket number?"*

---

## 4. Key Takeaways
- **Server 1** handles real-time CRM lookups and gracefully falls back on alternate search keys (like customer ID or email).
- **Server 2** guards historical audit trail integrity, providing explicit format guidance across the MCP JSON-RPC protocol.
- Both servers empower the central ReAct agent to recover autonomously without throwing unhandled exceptions.
